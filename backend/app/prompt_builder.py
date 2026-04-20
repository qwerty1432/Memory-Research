import os
import json
import re
from . import prompt_store


def get_phase_prompts(phase: int) -> list[str]:
    cfg = prompt_store.get_config()
    return cfg.get("phase_question_banks", {}).get(str(phase), [])


def get_phase_opening_message(phase: int) -> str:
    cfg = prompt_store.get_config()
    prompts = get_phase_prompts(phase)
    opening_msgs = cfg.get("phase_opening_messages", {})

    if not prompts:
        return opening_msgs.get("fallback", "Hey! I'm really glad you're here. Feel free to share whatever's on your mind.")

    template = opening_msgs.get(str(phase), "")
    if not template:
        return opening_msgs.get("fallback", "Hey! I'm really glad you're here. Feel free to share whatever's on your mind.")

    return template.replace("{first_question}", prompts[0])


def _get_cross_phase_bridge_instruction(next_prompt: str) -> str:
    cfg = prompt_store.get_config()
    bridge_map = cfg.get("bridge_instructions", {})
    normalized = (next_prompt or "").strip().lower()
    return bridge_map.get(normalized, "")


def build_phase_guided_messages(
    *,
    context: str,
    user_message: str,
    condition: str,
    phase: int,
    prompts_answered: int,
    total_prompts: int,
    next_prompt: str,
) -> list[dict]:
    cfg = prompt_store.get_config()
    system_template = cfg.get("guided_system_prompt", "")
    system_prompt = system_template.replace("{condition}", condition)

    bridge_instruction = _get_cross_phase_bridge_instruction(next_prompt)
    progress_prompt = (
        f"[Internal — never quote or show this block to the user] "
        f"Progress: {prompts_answered}/{total_prompts} topics covered. "
        f"Next topic to weave into your reply: {next_prompt}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    if context.strip():
        messages.append(
            {
                "role": "system",
                "content": f"Context from previous conversations:\n{context}",
            }
        )
        if bridge_instruction:
            messages.append({"role": "system", "content": bridge_instruction})
    messages.append({"role": "system", "content": progress_prompt})
    messages.append(
        {
            "role": "system",
            "content": (
                "Scope: The only new substantive topic you may introduce is the single line "
                "quoted in the internal block above. Do not preview, reference, or allude to "
                "any other upcoming interview topics that are not in that line."
            ),
        }
    )
    messages.append({"role": "user", "content": user_message})
    return messages


def build_phase_completion_messages(*, context: str, user_message: str, phase: int) -> list[dict]:
    cfg = prompt_store.get_config()
    system_template = cfg.get("phase_completion_prompt", "")
    system_prompt = system_template.replace("{phase}", str(phase))

    messages = [{"role": "system", "content": system_prompt}]
    if context.strip():
        messages.append(
            {
                "role": "system",
                "content": f"Context from previous conversations:\n{context}",
            }
        )
    messages.append({"role": "user", "content": user_message})
    return messages


def build_messages(context: str, user_message: str) -> list[dict]:
    cfg = prompt_store.get_config()
    tone = (os.getenv("CHAT_TONE") or "extroverted").strip().lower()
    if tone == "neutral":
        system_prompt = cfg.get("free_chat_prompt_neutral", "You are a friendly AI companion.")
    else:
        system_prompt = cfg.get("free_chat_prompt_extroverted", "You are a warm AI companion.")

    messages = [{"role": "system", "content": system_prompt}]

    if context.strip():
        messages.append({
            "role": "system",
            "content": f"Context from previous conversations:\n{context}"
        })

    messages.append({"role": "user", "content": user_message})
    return messages


def get_skip_confirmation_prompt_text() -> str:
    cfg = prompt_store.get_config()
    default = (
        "I'm not totally sure I understood — were you hoping to move on to the **next "
        "question**, or would you like to **stay on this one** and share more when you're "
        "ready? Either is fine. You can say **next** to skip, or **keep going** to stay."
    )
    return str(cfg.get("skip_confirmation_prompt") or default).strip() or default


def _clamp_score_int(v: object, lo: int, hi: int, default: int) -> int:
    try:
        iv = int(v)  # type: ignore[arg-type]
    except Exception:
        return default
    return max(lo, min(hi, iv))


def _normalize_assessment_outcome(raw: str) -> str:
    """Normalize model output to snake_case outcome id."""
    s = (raw or "").strip().lower().replace("-", "_")
    s = re.sub(r"\s+", "_", s)
    aliases = {
        "needs_follow_up": "needs_clarifying_followup",
        "need_clarifying_followup": "needs_clarifying_followup",
        "clarifying_followup": "needs_clarifying_followup",
        "skip_confirmation": "offer_skip_confirmation",
        "ambiguous_skip": "offer_skip_confirmation",
        "skip": "explicit_skip",
        "advance": "pending_advance",
        "stay": "pending_stay",
        "continue": "pending_stay",
    }
    return aliases.get(s, s)


def _fallback_unified_state(
    guided_mode: bool,
    pending_skip_confirmation: bool,
    *,
    reason: str,
) -> dict:
    o = "sufficient"
    if pending_skip_confirmation:
        o = "sufficient"
    elif not guided_mode:
        o = "sufficient"
    return {
        "relevance_score": 2,
        "effort_score": 2,
        "outcome": o,
        "followup_question": "",
        "assessment_fallback": True,
        "fallback_reason": reason,
    }


async def assess_guided_turn(
    last_assistant_prompt: str | None,
    user_message: str,
    *,
    guided_mode: bool,
    pending_skip_confirmation: bool,
    skip_confirmation_sent: bool,
    current_required_prompt: str | None,
    followups_used_for_prompt: int,
    max_followups: int = 3,
) -> dict:
    """
    Single LLM call: skip intent, ambiguous skip offer, sufficiency, and follow-up need.
    Used for guided Qualtrics/playground flow and (with guided_mode=False) for legacy free-chat assessments.
    """
    from .genai_client import call_genai

    cfg = prompt_store.get_config()
    user_template = str(cfg.get("guided_turn_assessment_user_template") or "").strip()
    system_content = str(
        cfg.get("guided_turn_assessment_system") or "You output strict JSON only."
    ).strip()
    if not user_template:
        return _fallback_unified_state(guided_mode, pending_skip_confirmation, reason="missing_template")

    at_cap = followups_used_for_prompt >= max_followups
    current_topic = (current_required_prompt or "").strip() or "(open conversation)"

    user_block = user_template.replace("{guided_interview_mode}", "yes" if guided_mode else "no")
    user_block = user_block.replace("{pending_skip_confirmation}", "yes" if pending_skip_confirmation else "no")
    user_block = user_block.replace(
        "{skip_confirmation_sent}", "yes" if skip_confirmation_sent else "no"
    )
    user_block = user_block.replace("{followups_used}", str(followups_used_for_prompt))
    user_block = user_block.replace("{max_followups}", str(max_followups))
    user_block = user_block.replace("{at_followup_cap}", "yes" if at_cap else "no")
    user_block = user_block.replace("{current_topic}", json.dumps(current_topic[:1200]))
    user_block = user_block.replace(
        "{last_assistant_prompt}",
        json.dumps((last_assistant_prompt or "").strip()[:1200]),
    )
    user_block = user_block.replace("{user_response}", json.dumps((user_message or "").strip()[:1200]))

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_block},
    ]

    try:
        raw_text = await call_genai(messages, stream=False, temperature=0.0, max_tokens=520)
    except Exception:
        return _fallback_unified_state(guided_mode, pending_skip_confirmation, reason="api_error")

    raw_text = (raw_text or "").strip()
    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text).strip()

    try:
        data = json.loads(raw_text)
    except Exception:
        return _fallback_unified_state(guided_mode, pending_skip_confirmation, reason="json_parse")

    outcome = _normalize_assessment_outcome(str(data.get("outcome") or ""))
    fq = str(data.get("followup_question") or "").strip()
    if len(fq) > 220:
        fq = fq[:220].rstrip()

    rel = _clamp_score_int(data.get("relevance_score"), 1, 3, 2)
    effort = _clamp_score_int(data.get("effort_score"), 1, 3, 2)

    if at_cap and outcome in ("needs_clarifying_followup", "offer_skip_confirmation"):
        outcome = "sufficient"
        fq = ""
    if skip_confirmation_sent and outcome == "offer_skip_confirmation":
        outcome = "sufficient"
        fq = ""

    if pending_skip_confirmation and outcome == "explicit_skip":
        outcome = "pending_advance"

    # Coerce invalid outcomes for mode
    if not guided_mode:
        if outcome not in ("sufficient", "needs_clarifying_followup"):
            outcome = "sufficient"
            fq = ""
    elif pending_skip_confirmation:
        if outcome not in (
            "pending_advance",
            "pending_stay",
            "sufficient",
            "needs_clarifying_followup",
        ):
            outcome = "sufficient"
            fq = ""
    else:
        if outcome not in (
            "explicit_skip",
            "sufficient",
            "needs_clarifying_followup",
            "offer_skip_confirmation",
        ):
            outcome = "sufficient"
            fq = ""

    if outcome != "needs_clarifying_followup":
        fq = ""
    return {
        "relevance_score": rel,
        "effort_score": effort,
        "outcome": outcome,
        "followup_question": fq,
        "unified_assessment": True,
    }


async def assess_effort_relevance(
    last_assistant_prompt: str | None,
    user_message: str,
) -> dict:
    """
    Legacy shape for callers expecting needs_followup + followup_question.
    Uses the same unified assessment in free-chat mode (one LLM call).
    """
    u = await assess_guided_turn(
        last_assistant_prompt,
        user_message,
        guided_mode=False,
        pending_skip_confirmation=False,
        skip_confirmation_sent=False,
        current_required_prompt=None,
        followups_used_for_prompt=0,
        max_followups=3,
    )
    need = u.get("outcome") == "needs_clarifying_followup"
    return {
        "relevance_score": u["relevance_score"],
        "effort_score": u["effort_score"],
        "needs_followup": need,
        "followup_question": u.get("followup_question") or "",
        "unified_assessment": True,
    }


async def maybe_build_followup_override(
    last_assistant_prompt: str | None,
    user_message: str,
    *,
    current_required_prompt: str | None = None,
    followups_used_for_prompt: int = 0,
    used_followups_for_prompt: list[str] | None = None,
    skip_confirmation_sent: bool = False,
    pending_skip_confirmation: bool = False,
) -> tuple[str | None, dict | None]:
    """
    Single LLM assessment (assess_guided_turn) decides skip vs sufficient vs follow-up vs skip-confirm offer.
    """
    cfg = prompt_store.get_config()
    max_followups = 3
    used_followups = [s.strip().lower() for s in (used_followups_for_prompt or []) if str(s).strip()]
    guided_mode = current_required_prompt is not None
    if not guided_mode:
        pending_skip_confirmation = False

    state = await assess_guided_turn(
        last_assistant_prompt,
        user_message,
        guided_mode=guided_mode,
        pending_skip_confirmation=pending_skip_confirmation,
        skip_confirmation_sent=skip_confirmation_sent,
        current_required_prompt=current_required_prompt,
        followups_used_for_prompt=followups_used_for_prompt,
        max_followups=max_followups,
    )

    outcome = str(state.get("outcome") or "sufficient")
    effort_result: dict = {
        "relevance_score": state["relevance_score"],
        "effort_score": state["effort_score"],
        "needs_followup": False,
        "followup_question": "",
        "unified_assessment": True,
        "assessment_outcome": outcome,
    }
    if state.get("assessment_fallback"):
        effort_result["assessment_fallback"] = True
        effort_result["fallback_reason"] = state.get("fallback_reason")

    # Pending skip-dialogue resolutions (same model call)
    if pending_skip_confirmation:
        if outcome == "pending_advance" or outcome == "explicit_skip":
            effort_result["user_skip"] = True
            return None, effort_result
        if outcome == "pending_stay":
            effort_result["resume_after_skip_prompt"] = True
            return None, effort_result
        # sufficient or needs_clarifying_followup: fall through to mapping below

    if guided_mode and outcome == "explicit_skip":
        effort_result["user_skip"] = True
        return None, effort_result

    if guided_mode and outcome == "offer_skip_confirmation":
        followup_text = get_skip_confirmation_prompt_text()
        effort_result["needs_followup"] = True
        effort_result["followup_question"] = followup_text
        effort_result["skip_confirmation_issued"] = True
        return followup_text, effort_result

    if outcome == "needs_clarifying_followup":
        followup_question = (state.get("followup_question") or "").strip()
        if guided_mode and current_required_prompt:
            if followup_question and current_required_prompt.lower() not in followup_question.lower():
                followup_question = f"Regarding {current_required_prompt.lower()}, {followup_question}"
        normalized = followup_question.strip().lower()
        if normalized in used_followups:
            if current_required_prompt:
                fallbacks = [
                    f"I'm curious -- what's one specific thing that stands out to you about {current_required_prompt.lower()}?",
                    "What's a concrete example that comes to mind?",
                    "If you picture it vividly, what detail jumps out first?",
                ]
            else:
                fallbacks = [
                    "What's one specific thing that stands out?",
                    "What's a concrete example that comes to mind?",
                    "If you picture it vividly, what jumps out first?",
                ]
            for fb in fallbacks:
                if fb.strip().lower() not in used_followups:
                    followup_question = fb
                    break
        if not followup_question.strip():
            followup_question = "What's one thing that first comes to mind for you?"
        effort_result["needs_followup"] = True
        effort_result["followup_question"] = followup_question
        return followup_question, effort_result

    # sufficient (and free-chat sufficient path)
    if followups_used_for_prompt >= max_followups and guided_mode:
        effort_result["followup_cap_reached"] = True
    return None, effort_result


async def extract_memories_from_conversation(
    user_message: str,
    existing_memories: list[str] = None
) -> list[str]:
    """
    Extract potential memory candidates from user message using LLM.

    CRITICAL: Only extracts from the user's message, NOT from assistant responses or inferences.
    """
    cfg = prompt_store.get_config()
    existing_context = ""
    if existing_memories:
        existing_context = "\n\nExisting memories (DO NOT extract these again):\n" + "\n".join(f"- {mem}" for mem in existing_memories[:20])

    user_template = cfg.get("memory_extraction_user_template", "")
    extraction_prompt = user_template.replace(
        "{user_message}", user_message
    ).replace(
        "{existing_context}", existing_context
    )

    system_content = cfg.get("memory_extraction_system",
        "You are a memory extraction assistant. Extract ONLY factual information that the user explicitly stated.")

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": extraction_prompt},
    ]

    from .genai_client import call_genai

    try:
        response = await call_genai(messages, stream=False, temperature=0.1, max_tokens=200)

        memories = []
        for line in response.strip().split("\n"):
            line = line.strip()
            if line and line.lower() != "none" and line.startswith("User"):
                memory_text = line
                if len(memory_text) > 200:
                    memory_text = memory_text[:200]
                memories.append(memory_text)

        return memories
    except Exception as e:
        print(f"Memory extraction error: {e}")
        return []
