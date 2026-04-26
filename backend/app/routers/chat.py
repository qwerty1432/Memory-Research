from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession
from ..database import get_db, SessionLocal
from .. import schemas, models, memory_manager, prompt_builder, logging
from ..models import Message, Session as SessionModel
from ..genai_client import call_genai, sanitize_companion_public_output, stream_genai
from uuid import UUID
import asyncio
import os
import json
import time
import random
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/chat", tags=["chat"])
QUALTRICS_PHASE_EVENT = "qualtrics_phase_session"
MIN_FOLLOWUPS_BEFORE_ADVANCE = 2
MAX_FOLLOWUPS_PER_PROMPT = 3
MAX_BG_EXTRACTION_TASKS = int(os.getenv("MAX_BG_EXTRACTION_TASKS", "2"))
_bg_extraction_semaphore = asyncio.Semaphore(MAX_BG_EXTRACTION_TASKS)
MAX_CONCURRENT_CHAT_REQUESTS = int(os.getenv("MAX_CONCURRENT_CHAT_REQUESTS", "24"))
CHAT_CONCURRENCY_ACQUIRE_TIMEOUT_SEC = float(
    os.getenv("CHAT_CONCURRENCY_ACQUIRE_TIMEOUT_SEC", "0.25")
)
SKIP_BG_EXTRACTION_WHEN_CHAT_SATURATED = (
    os.getenv("SKIP_BG_EXTRACTION_WHEN_CHAT_SATURATED", "true").strip().lower() == "true"
)
_chat_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHAT_REQUESTS)
GUIDED_DEBUG_LOGS = (os.getenv("GUIDED_DEBUG_LOGS", "false").strip().lower() == "true")
SKIP_RECONCILIATION_ENABLED = (
    os.getenv("SKIP_RECONCILIATION_ENABLED", "true").strip().lower() == "true"
)


async def _run_memory_extraction_limited(
    user_id: UUID,
    session_id: UUID,
    user_msg: str,
    cond: str,
    memory_phase: int | None,
):
    acquired = False
    try:
        await asyncio.wait_for(_bg_extraction_semaphore.acquire(), timeout=0.2)
        acquired = True
    except TimeoutError:
        print("[Chat] bg extraction skipped: worker limit reached")
        return

    bg_db = SessionLocal()
    try:
        existing_memories = memory_manager.get_all_existing_memories(user_id, session_id, bg_db)
        memory_candidates_text = await prompt_builder.extract_memories_from_conversation(
            user_msg, existing_memories
        )
        for candidate_text in memory_candidates_text:
            if not memory_manager.check_memory_duplicate(candidate_text, user_id, session_id, bg_db):
                auto_activate = cond in ["SESSION_AUTO", "PERSISTENT_AUTO"]
                memory_manager.create_memory_candidate(
                    user_id, session_id, candidate_text, bg_db, is_active=auto_activate,
                    phase=memory_phase,
                )
    except Exception as e:
        # Avoid recursive DB pressure by not writing another event when pool is saturated.
        print(f"[Chat] bg extraction error: {e}")
    finally:
        bg_db.close()
        if acquired:
            _bg_extraction_semaphore.release()


@router.get("/progress", response_model=schemas.PhaseStatus)
def get_progress(
    user_id: UUID,
    session_id: UUID,
    db: DBSession = Depends(get_db),
):
    """
    Return persisted single-block progress for the given session.
    Useful for Qualtrics iframe reloads so the UI can re-enable "Finish" correctly.
    """
    progress = logging.get_latest_progress(db, user_id, session_id) or {}

    current_phase = progress.get("current_phase", 1)
    current_prompt_index = progress.get("current_prompt_index", 0)
    followups_used_for_prompt = progress.get("followups_used_for_prompt", 0)
    phase_complete = progress.get("phase_complete", False)
    study_complete = progress.get("study_complete", False)

    phase_prompts = prompt_builder.get_phase_prompts(current_phase)
    total_prompts = len(phase_prompts)

    return schemas.PhaseStatus(
        phase=current_phase,
        prompts_answered=min(current_prompt_index, total_prompts),
        total_prompts=total_prompts,
        phase_complete=phase_complete,
        study_complete=study_complete,
        current_prompt_index=current_prompt_index,
        followups_used_for_prompt=followups_used_for_prompt,
    )


def _ensure_phase_prompt_order(
    phase_prompts: list[str],
    phase: int,
    phase_prompt_orders: dict[str, list[int]] | None,
) -> tuple[list[int], dict[str, list[int]]]:
    orders = dict(phase_prompt_orders or {})
    phase_key = str(phase)
    total = len(phase_prompts)
    existing = orders.get(phase_key) or []
    valid = (
        len(existing) == total
        and set(existing) == set(range(total))
    )
    if not valid:
        order = list(range(total))
        random.shuffle(order)
        orders[phase_key] = order
    return orders[phase_key], orders


def _prompts_for_order(phase_prompts: list[str], order: list[int]) -> list[str]:
    if not phase_prompts:
        return []
    if len(order) != len(phase_prompts):
        return phase_prompts
    return [phase_prompts[i] for i in order if 0 <= i < len(phase_prompts)]


@router.post("/advance", response_model=schemas.AdvancePhaseResponse)
def advance_phase(
    request: schemas.AdvancePhaseRequest,
    db: DBSession = Depends(get_db),
):
    """
    Single-block mode helper to advance from Phase 1->2 or 2->3 after the phase is complete.
    Does NOT notify Qualtrics; frontend controls that (only at study completion).
    """
    progress = _get_progress_state(db, request.user_id, request.session_id)
    current_phase = progress["current_phase"]
    current_prompt_index = progress["current_prompt_index"]
    followups_used = progress["followups_used_for_prompt"]
    used_followups_for_prompt = progress["used_followups_for_prompt"]
    phase_complete = progress["phase_complete"]
    study_complete = progress["study_complete"]
    phase_prompt_orders = progress["phase_prompt_orders"]

    if study_complete:
        raise HTTPException(status_code=400, detail="Study already complete")

    if not phase_complete:
        raise HTTPException(status_code=400, detail="Phase not complete")

    if current_phase >= 3:
        raise HTTPException(status_code=400, detail="No next phase available")

    # Advance to next phase and reset prompt/followup tracking
    next_phase = current_phase + 1
    current_phase = next_phase
    current_prompt_index = 0
    followups_used = 0
    used_followups_for_prompt = []
    phase_complete = False
    study_complete = False

    phase_prompts = prompt_builder.get_phase_prompts(current_phase)
    total_prompts = len(phase_prompts)

    phase_order, phase_prompt_orders = _ensure_phase_prompt_order(
        phase_prompts, current_phase, phase_prompt_orders
    )
    ordered_prompts = _prompts_for_order(phase_prompts, phase_order)
    _update_progress_state(
        db,
        request.user_id,
        request.session_id,
        current_phase=current_phase,
        current_prompt_index=current_prompt_index,
        followups_used_for_prompt=followups_used,
        used_followups_for_prompt=used_followups_for_prompt,
        phase_complete=phase_complete,
        study_complete=study_complete,
        pending_skip_confirmation=False,
        skip_confirmation_sent=False,
        phase_prompt_orders=phase_prompt_orders,
    )
    first_prompt = ordered_prompts[0] if ordered_prompts else None
    opening_message = prompt_builder.get_phase_opening_message_for_question(
        current_phase, first_prompt
    )
    assistant_opening = Message(
        session_id=request.session_id,
        role="assistant",
        content=opening_message,
    )
    db.add(assistant_opening)
    db.commit()
    logging.log_message_received(db, request.user_id, request.session_id, opening_message)

    return schemas.AdvancePhaseResponse(
        phase_status=schemas.PhaseStatus(
            phase=current_phase,
            prompts_answered=0,
            total_prompts=total_prompts,
            phase_complete=False,
            study_complete=False,
            current_prompt_index=0,
            followups_used_for_prompt=0,
        ),
        opening_message=opening_message,
    )


def _resolve_session_phase(db: DBSession, user_id: UUID, session_id: UUID, explicit_phase: int | None) -> int | None:
    """Legacy: resolve phase from events. For single-block mode, use _get_progress_state instead."""
    if explicit_phase in (1, 2, 3):
        return explicit_phase
    phase_events = (
        db.query(models.Event)
        .filter(
            models.Event.user_id == user_id,
            models.Event.type == QUALTRICS_PHASE_EVENT,
        )
        .order_by(models.Event.created_at.desc())
        .all()
    )
    target_session_id = str(session_id)
    for event in phase_events:
        payload = event.payload_json or {}
        if str(payload.get("session_id")) != target_session_id:
            continue
        phase = payload.get("phase")
        try:
            phase_int = int(phase)
        except (TypeError, ValueError):
            continue
        if phase_int in (1, 2, 3):
            return phase_int
    return None


def _get_progress_state(db: DBSession, user_id: UUID, session_id: UUID) -> dict:
    """
    Get current progress state for single-block mode.
    Returns dict with: current_phase, current_prompt_index, followups_used_for_prompt, used_followups_for_prompt, phase_complete, study_complete.
    Defaults to phase 1, prompt 0 if no progress found.
    """
    progress = logging.get_latest_progress(db, user_id, session_id)
    if progress:
        return {
            "current_phase": progress.get("current_phase", 1),
            "current_prompt_index": progress.get("current_prompt_index", 0),
            "followups_used_for_prompt": progress.get("followups_used_for_prompt", 0),
            "used_followups_for_prompt": progress.get("used_followups_for_prompt", []) or [],
            "phase_complete": progress.get("phase_complete", False),
            "study_complete": progress.get("study_complete", False),
            "pending_skip_confirmation": progress.get("pending_skip_confirmation", False),
            "skip_confirmation_sent": progress.get("skip_confirmation_sent", False),
            "phase_prompt_orders": progress.get("phase_prompt_orders", {}) or {},
        }
    # Default: start at phase 1, prompt 0
    return {
        "current_phase": 1,
        "current_prompt_index": 0,
        "followups_used_for_prompt": 0,
        "used_followups_for_prompt": [],
        "phase_complete": False,
        "study_complete": False,
        "pending_skip_confirmation": False,
        "skip_confirmation_sent": False,
        "phase_prompt_orders": {},
    }


def _update_progress_state(
    db: DBSession,
    user_id: UUID,
    session_id: UUID,
    *,
    current_phase: int,
    current_prompt_index: int,
    followups_used_for_prompt: int,
    used_followups_for_prompt: list[str],
    phase_complete: bool,
    study_complete: bool,
    pending_skip_confirmation: bool = False,
    skip_confirmation_sent: bool = False,
    phase_prompt_orders: dict[str, list[int]] | None = None,
):
    """Update progress state and log it."""
    logging.log_progress_update(
        db,
        user_id,
        session_id,
        current_phase=current_phase,
        current_prompt_index=current_prompt_index,
        followups_used_for_prompt=followups_used_for_prompt,
        used_followups_for_prompt=used_followups_for_prompt,
        phase_complete=phase_complete,
        study_complete=study_complete,
        pending_skip_confirmation=pending_skip_confirmation,
        skip_confirmation_sent=skip_confirmation_sent,
        phase_prompt_orders=phase_prompt_orders,
    )


@router.post("", response_model=schemas.ChatResponse)
async def chat(request: schemas.ChatRequest, db: DBSession = Depends(get_db)):
    """Handle chat message and return response"""
    if _chat_request_semaphore.locked():
        raise HTTPException(
            status_code=503,
            detail=(
                "Chat service is temporarily overloaded. "
                "Please retry in a few seconds."
            ),
        )

    # Verify user exists
    user = db.query(models.User).filter(models.User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify session exists
    session = db.query(SessionModel).filter(SessionModel.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get user's condition
    condition = user.condition_id
    
    # Get context based on condition
    context = memory_manager.get_context(request.user_id, request.session_id, condition, db)
    
    # Determine mode: single-block (no explicit phase) or legacy phase-specific
    is_single_block_mode = request.phase is None
    
    if is_single_block_mode:
        # Single-block mode: use progress state
        progress = _get_progress_state(db, request.user_id, request.session_id)
        current_phase = progress["current_phase"]
        current_prompt_index = progress["current_prompt_index"]
        followups_used = progress["followups_used_for_prompt"]
        used_followups_for_prompt = progress["used_followups_for_prompt"]
        phase_complete = progress["phase_complete"]
        study_complete = progress["study_complete"]
        pending_skip_confirmation = progress["pending_skip_confirmation"]
        skip_confirmation_sent = progress["skip_confirmation_sent"]
        phase_prompt_orders = progress["phase_prompt_orders"]
    else:
        # Legacy mode: use explicit phase
        current_phase = request.phase
        # For legacy mode, estimate prompt index from user message count
        existing_user_count = (
            db.query(Message)
            .filter(Message.session_id == request.session_id, Message.role == "user")
            .count()
        )
        current_prompt_index = min(existing_user_count, 5)  # Cap at 5 (0-indexed, so 6 prompts)
        followups_used = 0  # Legacy mode doesn't track follow-ups per prompt
        used_followups_for_prompt: list[str] = []
        phase_complete = False
        study_complete = False
        phase_prompt_orders = {}
    
    phase_status = None
    
    # Log message sent
    logging.log_message_sent(db, request.user_id, request.session_id, request.message)

    # Get last assistant message for follow-up evaluation
    last_assistant = (
        db.query(Message)
        .filter(Message.session_id == request.session_id, Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .first()
    )
    
    # Determine current required prompt (if in guided mode)
    current_required_prompt = None
    ordered_phase_prompts: list[str] = []
    if is_single_block_mode and not study_complete:
        phase_prompts = prompt_builder.get_phase_prompts(current_phase)
        order, phase_prompt_orders = _ensure_phase_prompt_order(
            phase_prompts, current_phase, phase_prompt_orders
        )
        ordered_phase_prompts = _prompts_for_order(phase_prompts, order)
        if current_prompt_index < len(ordered_phase_prompts):
            current_required_prompt = ordered_phase_prompts[current_prompt_index]
    
    # Evaluate sufficiency and get follow-up override (if needed)
    t_start = time.time()
    followup_override = None
    effort_result = None
    ran_followup_check = False
    if is_single_block_mode and not study_complete and current_required_prompt:
        t_effort = time.time()
        initial_pending_skip = pending_skip_confirmation
        followup_override, effort_result = await prompt_builder.maybe_build_followup_override(
            last_assistant.content if last_assistant else None,
            request.message,
            current_required_prompt=current_required_prompt,
            followups_used_for_prompt=followups_used,
            used_followups_for_prompt=used_followups_for_prompt,
            skip_confirmation_sent=skip_confirmation_sent,
            pending_skip_confirmation=pending_skip_confirmation,
        )
        ran_followup_check = True

        if effort_result and effort_result.get("skip_confirmation_issued"):
            pending_skip_confirmation = True
            skip_confirmation_sent = True
        elif initial_pending_skip:
            # Resolved skip-vs-continue dialog (stay, skip, substantive reply, or clarifying follow-up).
            pending_skip_confirmation = False

        # Reconciliation layer: if the LLM assessment misses clear move-on intent, coerce to skip.
        if (
            SKIP_RECONCILIATION_ENABLED
            and
            effort_result is not None
            and not pending_skip_confirmation
            and not effort_result.get("user_skip", False)
            and prompt_builder.has_natural_language_skip_intent(request.message)
        ):
            effort_result["user_skip"] = True
            effort_result["assessment_reconciled_skip"] = True
            effort_result["needs_followup"] = False
            followup_override = None

        print(f"[Chat] effort_check: {time.time()-t_effort:.1f}s | override={'yes' if followup_override else 'no'}")
        if effort_result is not None:
            logging.log_effort_check(
                db,
                request.user_id,
                request.session_id,
                user_message=request.message,
                result=effort_result,
            )
    
    # Handle progress state updates for single-block mode
    if is_single_block_mode and not study_complete:
        # Single-block guided mode
        phase_prompts = prompt_builder.get_phase_prompts(current_phase)
        order, phase_prompt_orders = _ensure_phase_prompt_order(
            phase_prompts, current_phase, phase_prompt_orders
        )
        ordered_phase_prompts = _prompts_for_order(phase_prompts, order)
        total_prompts = len(ordered_phase_prompts)

        # If the phase is already complete, we should not advance counters further.
        # We keep progress frozen until the UI calls /chat/advance.
        if phase_complete:
            should_advance_prompt = False
            followup_override = None
            effort_result = None
            pending_skip_confirmation = False
        else:
        
            # Determine if we should advance to next prompt or phase
            should_advance_prompt = False
            if followup_override is None:
                # No follow-up override - check if response was sufficient
                if not ran_followup_check:
                    # No required prompt / follow-up path ran — do not advance (avoids spurious jumps)
                    should_advance_prompt = False
                elif effort_result is None:
                    # Defensive: should not happen after maybe_build_followup_override
                    should_advance_prompt = False
                else:
                    user_skip = bool(effort_result.get("user_skip", False))
                    resume_after_skip_prompt = bool(
                        effort_result.get("resume_after_skip_prompt", False)
                    )
                    needs_followup = bool(effort_result.get("needs_followup", False))

                    # 1) Explicit/confirmed skip can always advance.
                    if user_skip:
                        should_advance_prompt = True
                    # 2) "Keep going" from skip confirmation must stay on current topic.
                    elif resume_after_skip_prompt:
                        should_advance_prompt = False
                    # 3) Insufficient answer: ask follow-up up to cap; then force advance.
                    elif needs_followup:
                        if followups_used >= MAX_FOLLOWUPS_PER_PROMPT:
                            should_advance_prompt = True
                        else:
                            followup_override = (
                                effort_result.get("followup_question")
                                or prompt_builder.build_forced_followup_question(
                                    current_required_prompt,
                                    used_followups_for_prompt,
                                )
                            )
                            effort_result["needs_followup"] = True
                            effort_result["followup_question"] = followup_override
                            should_advance_prompt = False
                    # 4) Sufficient answer: require 2 follow-ups before advancing.
                    else:
                        if followups_used < MIN_FOLLOWUPS_BEFORE_ADVANCE:
                            followup_override = prompt_builder.build_forced_followup_question(
                                current_required_prompt,
                                used_followups_for_prompt,
                            )
                            effort_result["needs_followup"] = True
                            effort_result["followup_question"] = followup_override
                            should_advance_prompt = False
                        else:
                            should_advance_prompt = True
            # Invariant guardrail: do not allow a stalled turn with no follow-up and no advance.
            if (
                ran_followup_check
                and not should_advance_prompt
                and followup_override is None
                and effort_result is not None
                and not effort_result.get("user_skip", False)
                and not effort_result.get("resume_after_skip_prompt", False)
            ):
                followup_override = prompt_builder.build_forced_followup_question(
                    current_required_prompt,
                    used_followups_for_prompt,
                )
                effort_result["needs_followup"] = True
                effort_result["followup_question"] = followup_override
            # If followup_override is not None, we're asking a follow-up - don't advance
            
            if should_advance_prompt:
                skip_transition = bool(effort_result and effort_result.get("user_skip"))
                # Advance to next prompt
                current_prompt_index += 1
                followups_used = 0  # Reset follow-up counter for new prompt
                used_followups_for_prompt = []
                pending_skip_confirmation = False
                skip_confirmation_sent = False
                if skip_transition and current_prompt_index < total_prompts:
                    followup_override = prompt_builder.build_skip_transition_message(
                        ordered_phase_prompts[current_prompt_index]
                    )
                
                # Check if phase is complete
                if current_prompt_index >= total_prompts:
                    phase_complete = True
                    if skip_transition:
                        followup_override = prompt_builder.build_skip_transition_message(None)
                    # IMPORTANT (single-block Qualtrics flow):
                    # Do NOT auto-advance to the next phase here. We wait for the UI "Continue"
                    # action to call /chat/advance, which will move Phase 1->2 or 2->3 and
                    # inject the next phase opening message.
                    if current_phase >= 3:
                        # All phases complete
                        study_complete = True
            elif followup_override is not None:
                # Asking a follow-up - increment counter but stay on same prompt
                followups_used = min(followups_used + 1, MAX_FOLLOWUPS_PER_PROMPT)
                used_followups_for_prompt = used_followups_for_prompt + [followup_override]
        
        # Update progress state (always update, even if asking follow-up)
        if GUIDED_DEBUG_LOGS:
            logging.log_event(
                db,
                "guided_progress_decision",
                request.user_id,
                {
                    "session_id": str(request.session_id),
                    "current_phase": current_phase,
                    "current_prompt_index": current_prompt_index,
                    "total_prompts": total_prompts,
                    "should_advance_prompt": bool(should_advance_prompt),
                    "followups_used_for_prompt": followups_used,
                    "assessment_outcome": (effort_result or {}).get("assessment_outcome"),
                    "user_skip": bool((effort_result or {}).get("user_skip")),
                    "needs_followup": bool((effort_result or {}).get("needs_followup")),
                },
            )
        _update_progress_state(
            db,
            request.user_id,
            request.session_id,
            current_phase=current_phase,
            current_prompt_index=current_prompt_index,
            followups_used_for_prompt=followups_used,
            used_followups_for_prompt=used_followups_for_prompt,
            phase_complete=phase_complete,
            study_complete=study_complete,
            pending_skip_confirmation=pending_skip_confirmation,
            skip_confirmation_sent=skip_confirmation_sent,
            phase_prompt_orders=phase_prompt_orders,
        )
        
        # Build phase status
        phase_prompts = prompt_builder.get_phase_prompts(current_phase)
        total_prompts = len(phase_prompts)
        phase_status = {
            "phase": current_phase,
            # prompts_answered is a count; current_prompt_index is the 0-based index of the active question
            "prompts_answered": min(current_prompt_index, total_prompts),
            "total_prompts": total_prompts,
            "phase_complete": phase_complete,
            "study_complete": study_complete,
            "current_prompt_index": current_prompt_index,
            "followups_used_for_prompt": followups_used,
        }
    
    # Build messages for GenAI API (only if we're not overriding with a follow-up)
    messages = None
    if not followup_override:
        if is_single_block_mode:
            # Build response messages for single-block guided interview.
            if study_complete:
                # Study complete - thank user
                messages = prompt_builder.build_phase_completion_messages(
                    context=context,
                    user_message=request.message,
                    phase=3,  # Final phase
                )
            elif phase_complete and current_phase < 3:
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a warm, friendly conversation partner.\n"
                            f"You've just finished chatting through all the topics in this set.\n"
                            "Respond by:\n"
                            "1) Reacting genuinely to what they just shared.\n"
                            "2) Letting them know they did great and can click the 'Continue' button below whenever they're ready for the next set of topics.\n"
                            "Keep it brief, warm, and natural. Do not ask any new question."
                        ),
                    },
                    {"role": "system", "content": f"Context from previous conversations:\n{context}"} if context.strip() else None,
                    {"role": "user", "content": request.message},
                ]
                messages = [m for m in messages if m is not None]
            elif current_prompt_index < total_prompts:
                # Continue with current phase
                if not ordered_phase_prompts:
                    phase_prompts = prompt_builder.get_phase_prompts(current_phase)
                    order, phase_prompt_orders = _ensure_phase_prompt_order(
                        phase_prompts, current_phase, phase_prompt_orders
                    )
                    ordered_phase_prompts = _prompts_for_order(phase_prompts, order)
                next_prompt = ordered_phase_prompts[current_prompt_index]
                messages = prompt_builder.build_phase_guided_messages(
                    context=context,
                    user_message=request.message,
                    condition=condition,
                    phase=current_phase,
                    prompts_answered=current_prompt_index,
                    total_prompts=total_prompts,
                    current_prompt=next_prompt,
                    followups_used_for_prompt=followups_used,
                    min_followups_before_advance=MIN_FOLLOWUPS_BEFORE_ADVANCE,
                )
            else:
                # Shouldn't happen, but fallback
                messages = prompt_builder.build_messages(context, request.message)
        elif not is_single_block_mode and current_phase is not None:
            # Legacy phase-specific mode
            phase_prompts = prompt_builder.get_phase_prompts(current_phase)
            total_prompts = len(phase_prompts)
            existing_user_count = (
                db.query(Message)
                .filter(Message.session_id == request.session_id, Message.role == "user")
                .count()
            )
            prompts_answered = existing_user_count + 1
            answered_capped = min(prompts_answered, total_prompts)
            phase_complete = answered_capped >= total_prompts
            phase_status = {
                "phase": current_phase,
                "prompts_answered": answered_capped,
                "total_prompts": total_prompts,
                "phase_complete": phase_complete,
                "study_complete": False,
                "current_prompt_index": answered_capped - 1,
                "followups_used_for_prompt": 0,
            }
            if phase_complete:
                messages = prompt_builder.build_phase_completion_messages(
                    context=context,
                    user_message=request.message,
                    phase=current_phase,
                )
            else:
                next_prompt = phase_prompts[answered_capped]
                messages = prompt_builder.build_phase_guided_messages(
                    context=context,
                    user_message=request.message,
                    condition=condition,
                    phase=current_phase,
                    prompts_answered=answered_capped,
                    total_prompts=total_prompts,
                    current_prompt=next_prompt,
                    followups_used_for_prompt=0,
                    min_followups_before_advance=MIN_FOLLOWUPS_BEFORE_ADVANCE,
                )
        else:
            # Free-form chat mode (not in guided phase mode)
            messages = prompt_builder.build_messages(context, request.message)
    
    # Call GenAI API (or return follow-up override)
    if followup_override:
        response_text = followup_override
        print(f"[Chat] response: followup_override (no LLM call)")
    else:
        t_llm = time.time()
        try:
            response_text = await call_genai(messages, stream=False, max_tokens=768)
            print(f"[Chat] response: LLM ok in {time.time()-t_llm:.1f}s")
        except Exception as e:
            error_msg = str(e)
            print(f"[Chat] response: LLM attempt1 FAILED in {time.time()-t_llm:.1f}s — {error_msg}")
            logging.log_error(db, "error_chat_api", request.user_id, f"First attempt: {error_msg}")
            t_retry = time.time()
            try:
                response_text = await call_genai(messages, stream=False, max_tokens=768)
                print(f"[Chat] response: LLM retry ok in {time.time()-t_retry:.1f}s")
            except Exception as retry_error:
                error_msg = str(retry_error)
                print(f"[Chat] response: LLM retry FAILED in {time.time()-t_retry:.1f}s — {error_msg}")
                logging.log_error(db, "error_chat_api", request.user_id, f"Retry failed: {error_msg}")
                response_text = "Response unavailable. Please try again."
    
    # Save user message
    user_message = Message(
        session_id=request.session_id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    
    # Save assistant response
    assistant_message = Message(
        session_id=request.session_id,
        role="assistant",
        content=response_text
    )
    db.add(assistant_message)
    db.commit()
    
    # Log message received
    logging.log_message_received(db, request.user_id, request.session_id, response_text)
    
    # Fire-and-forget: extract memories in the background so the user
    # gets the chat response immediately without waiting for a third LLM call.
    extraction_phase = current_phase if current_phase in (1, 2, 3) else None
    if SKIP_BG_EXTRACTION_WHEN_CHAT_SATURATED and _chat_request_semaphore.locked():
        print("[Chat] bg extraction skipped: chat concurrency saturated")
    else:
        asyncio.create_task(
            _run_memory_extraction_limited(
                request.user_id,
                request.session_id,
                request.message,
                condition,
                extraction_phase,
            )
        )

    all_candidates = memory_manager.get_memory_candidates(request.user_id, request.session_id, db)

    print(
        f"[Chat] TOTAL: {time.time()-t_start:.1f}s | "
        f"phase={current_phase} prompt_idx={current_prompt_index}"
    )

    return {
        "response": response_text,
        "memory_candidates": [schemas.MemoryResponse.model_validate(m) for m in all_candidates],
        "phase_status": phase_status,
    }


@router.post("/stream")
async def chat_stream(request: schemas.ChatRequest, db: DBSession = Depends(get_db)):
    """Stream chat response using Server-Sent Events"""
    # Verify user and session
    user = db.query(models.User).filter(models.User.user_id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    session = db.query(SessionModel).filter(SessionModel.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get context and build messages
    condition = user.condition_id
    context = memory_manager.get_context(request.user_id, request.session_id, condition, db)
    
    # Log message sent
    logging.log_message_sent(db, request.user_id, request.session_id, request.message)

    # Effort / relevance check (may override assistant response with a follow-up question)
    last_assistant = (
        db.query(Message)
        .filter(Message.session_id == request.session_id, Message.role == "assistant")
        .order_by(Message.created_at.desc())
        .first()
    )
    followup_override, effort_result = await prompt_builder.maybe_build_followup_override(
        last_assistant.content if last_assistant else None,
        request.message,
    )
    if effort_result is not None:
        logging.log_effort_check(
            db,
            request.user_id,
            request.session_id,
            user_message=request.message,
            result=effort_result,
        )

    messages = None
    if not followup_override:
        messages = prompt_builder.build_messages(context, request.message)
    
    async def generate():
        try:
            response_text = ""
            if followup_override:
                response_text = followup_override
                yield {"data": json.dumps({"token": response_text})}
            else:
                # Stream from GenAI, then sanitize (reasoning models may emit planning in content).
                raw = ""
                async for chunk in stream_genai(messages):
                    raw += chunk
                response_text = sanitize_companion_public_output(raw)
                if response_text:
                    yield {"data": json.dumps({"token": response_text})}
            
            # Save messages to database
            user_message = Message(
                session_id=request.session_id,
                role="user",
                content=request.message
            )
            db.add(user_message)
            
            assistant_message = Message(
                session_id=request.session_id,
                role="assistant",
                content=response_text
            )
            db.add(assistant_message)
            db.commit()
            
            logging.log_message_received(db, request.user_id, request.session_id, response_text)
            
            # Extract and create memory candidates
            try:
                if request.phase is not None:
                    stream_memory_phase = request.phase if request.phase in (1, 2, 3) else None
                else:
                    stream_memory_phase = _get_progress_state(db, request.user_id, request.session_id)[
                        "current_phase"
                    ]
                    stream_memory_phase = stream_memory_phase if stream_memory_phase in (1, 2, 3) else None

                # Get existing memories for deduplication
                existing_memories = memory_manager.get_all_existing_memories(
                    request.user_id,
                    request.session_id,
                    db
                )
                
                # Extract memories from USER MESSAGE ONLY (not assistant response)
                memory_candidates_text = await prompt_builder.extract_memories_from_conversation(
                    request.message,  # Only user message, no assistant response
                    existing_memories
                )
                
                # Filter out duplicates and create memory candidates
                for candidate_text in memory_candidates_text:
                    # Check if this is a duplicate
                    if not memory_manager.check_memory_duplicate(
                        candidate_text,
                        request.user_id,
                        request.session_id,
                        db
                    ):
                        auto_activate = condition in ["SESSION_AUTO", "PERSISTENT_AUTO"]
                        # Not a duplicate, create the candidate
                        memory = memory_manager.create_memory_candidate(
                            request.user_id,
                            request.session_id,
                            candidate_text,
                            db,
                            is_active=auto_activate,
                            phase=stream_memory_phase,
                        )
                        if auto_activate:
                            logging.log_memory_approved(db, request.user_id, memory.memory_id)
                        else:
                            logging.log_memory_created(db, request.user_id, memory.memory_id)
            except Exception as e:
                logging.log_error(db, "error_memory_extraction", request.user_id, str(e))
            
            # Send final candidates
            all_candidates = memory_manager.get_memory_candidates(request.user_id, request.session_id, db)
            yield {"data": json.dumps({"done": True, "candidates": [{"memory_id": str(m.memory_id), "text": m.text} for m in all_candidates]})}
            
        except Exception as e:
            logging.log_error(db, "error_chat_api", request.user_id, str(e))
            yield {"data": json.dumps({"error": "Response unavailable. Please try again."})}
    
    return EventSourceResponse(generate())

