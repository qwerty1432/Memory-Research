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

