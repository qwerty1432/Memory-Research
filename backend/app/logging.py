from sqlalchemy.orm import Session
from .models import Event
from typing import Optional
from uuid import UUID
import json


def log_event(
    db: Session,
    event_type: str,
    user_id: Optional[UUID] = None,
    payload: Optional[dict] = None
):
    """Log an event to the events table"""
    event = Event(
        user_id=user_id,
        type=event_type,
        payload_json=payload if payload else None
    )
    db.add(event)
    db.commit()


def log_message_sent(db: Session, user_id: UUID, session_id: UUID, message: str):
    """Log a message sent event"""
    log_event(
        db,
        "message_sent",
        user_id,
        {
            "session_id": str(session_id),
            "message": message[:500]  # Truncate for logging
        }
    )


def log_message_received(db: Session, user_id: UUID, session_id: UUID, response: str):
    """Log a message received event"""
    log_event(
        db,
        "message_received",
        user_id,
        {
            "session_id": str(session_id),
            "response": response[:500]  # Truncate for logging
        }
    )


def log_memory_created(db: Session, user_id: UUID, memory_id: UUID):
    """Log a memory created event"""
    log_event(
        db,
        "memory_created",
        user_id,
        {"memory_id": str(memory_id)}
    )


def log_memory_approved(db: Session, user_id: UUID, memory_id: UUID):
    """Log a memory approved event"""
    log_event(
        db,
        "memory_approved",
        user_id,
        {"memory_id": str(memory_id)}
    )


def log_memory_rejected(db: Session, user_id: UUID, memory_id: UUID):
    """Log a memory rejected (deleted) event"""
    log_event(
        db,
        "memory_rejected",
        user_id,
        {"memory_id": str(memory_id)}
    )


def log_memory_edited(db: Session, user_id: UUID, memory_id: UUID):
    """Log a memory edited event"""
    log_event(
        db,
        "memory_edited",
        user_id,
        {"memory_id": str(memory_id)}
    )


def log_memory_deleted(db: Session, user_id: UUID, memory_id: UUID):
    """Log a memory deleted event"""
    log_event(
        db,
        "memory_deleted",
        user_id,
        {"memory_id": str(memory_id)}
    )


def log_session_started(db: Session, user_id: UUID, session_id: UUID):
    """Log a session started event"""
    log_event(
        db,
        "session_started",
        user_id,
        {"session_id": str(session_id)}
    )


def log_session_ended(db: Session, user_id: UUID, session_id: UUID):
    """Log a session ended event"""
    log_event(
        db,
        "session_ended",
        user_id,
        {"session_id": str(session_id)}
    )


def log_condition_assigned(db: Session, user_id: UUID, condition_id: str):
    """Log a condition assigned event"""
    log_event(
        db,
        "condition_assigned",
        user_id,
        {"condition_id": condition_id}
    )


def log_condition_changed(db: Session, user_id: UUID, condition_id: str):
    """Log a condition changed event"""
    log_event(
        db,
        "condition_changed",
        user_id,
        {"condition_id": condition_id}
    )


def log_error(db: Session, error_type: str, user_id: Optional[UUID], error_message: str):
    """Log an error event"""
    log_event(
        db,
        error_type,
        user_id,
        {"error": error_message}
    )


def log_effort_check(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    *,
    user_message: str,
    result: dict
):
    """
    Log effort/relevance assessment for a user message.
    Stored in `events.payload_json` to avoid schema changes.
    """
    payload = {
        "session_id": str(session_id),
        "user_message": user_message[:500],
        "result": result,
    }
    log_event(db, "effort_check", user_id, payload)


def log_progress_update(
    db: Session,
    user_id: UUID,
    session_id: UUID,
    *,
    current_phase: int,
    current_prompt_index: int,
    followups_used_for_prompt: int,
    used_followups_for_prompt: list[str] | None = None,
    phase_complete: bool,
    study_complete: bool,
    pending_skip_confirmation: bool = False,
    skip_confirmation_sent: bool = False,
    phase_prompt_orders: dict[str, list[int]] | None = None,
    name_collected: bool = True,
    preferred_name: str | None = None,
    transition_bridge: bool = False,
):
    """
    Log progress state update for single-block multi-phase flow.

    Stores: current_phase, current_prompt_index, followups_used_for_prompt, phase_complete,
    study_complete, pending_skip_confirmation, skip_confirmation_sent.

    The ``name_collected`` / ``preferred_name`` keys carry the result of the
    one-time name-collection turn that runs at the start of a fresh session
    (Issue 7). They default to a "name already handled" state so legacy
    sessions and resumed flows are unaffected.

    The ``transition_bridge`` key is a research-instrumentation flag (Issue 2):
    set to ``True`` when the assistant's reply for this turn was steered by a
    cross-topic bridge instruction so analyses can distinguish bridge-introduction
    turns from clarifying follow-ups in the event log.
    """
    payload = {
        "session_id": str(session_id),
        "current_phase": current_phase,
        "current_prompt_index": current_prompt_index,
        "followups_used_for_prompt": followups_used_for_prompt,
        "used_followups_for_prompt": used_followups_for_prompt or [],
        "phase_complete": phase_complete,
        "study_complete": study_complete,
        "pending_skip_confirmation": pending_skip_confirmation,
        "skip_confirmation_sent": skip_confirmation_sent,
        "phase_prompt_orders": phase_prompt_orders or {},
        "name_collected": name_collected,
        "preferred_name": preferred_name,
        "transition_bridge": transition_bridge,
    }
    log_event(db, "progress_update", user_id, payload)


def get_latest_progress(
    db: Session,
    user_id: UUID,
    session_id: UUID,
) -> dict | None:
    """
    Get the latest progress state for a session.
    Returns dict with: current_phase, current_prompt_index, followups_used_for_prompt, phase_complete,
    study_complete, pending_skip_confirmation, skip_confirmation_sent.
    Returns None if no progress found.
    """
    events = (
        db.query(Event)
        .filter(
            Event.user_id == user_id,
            Event.type == "progress_update",
        )
        .order_by(Event.created_at.desc())
        .all()
    )
    target_session_id = str(session_id)
    for event in events:
        payload = event.payload_json or {}
        if str(payload.get("session_id")) != target_session_id:
            continue
        return payload
    return None

