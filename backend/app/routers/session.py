from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..database import get_db
from .. import schemas, models, logging, memory_manager
from ..models import Session as SessionModel, Message
from uuid import UUID, uuid4
from datetime import datetime
from typing import List

router = APIRouter(prefix="/session", tags=["session"])


@router.post("", response_model=schemas.SessionResponse, status_code=201)
def create_session(session_data: schemas.SessionCreate, db: Session = Depends(get_db)):
    """Create a new session for a user"""
    user_id = session_data.user_id
    # Verify user exists
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # End current active session if exists
    active_session = db.query(SessionModel).filter(
        SessionModel.user_id == user_id,
        SessionModel.ended_at == None
    ).first()
    
    if active_session:
        active_session.ended_at = datetime.utcnow()
        logging.log_session_ended(db, user_id, active_session.session_id)
        
        # Cleanup session memories if in ephemeral mode
        if user.condition_id in ["SESSION_AUTO", "SESSION_USER"]:
            memory_manager.cleanup_session_memories(active_session.session_id, db)
    
    # Create new session
    new_session = SessionModel(
        session_id=uuid4(),
        user_id=user_id
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    logging.log_session_started(db, user_id, new_session.session_id)
    
    return new_session


@router.get("/{session_id}", response_model=schemas.SessionResponse)
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    """Get session by ID"""
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/user/{user_id}", response_model=List[schemas.SessionResponse])
def get_user_sessions(user_id: UUID, db: Session = Depends(get_db)):
    """Get all sessions for a user"""
    sessions = db.query(SessionModel).filter(
        SessionModel.user_id == user_id
    ).order_by(desc(SessionModel.started_at)).all()
    return sessions


@router.get("/{session_id}/messages", response_model=List[schemas.MessageResponse])
def get_session_messages(session_id: UUID, db: Session = Depends(get_db)):
    """Get all messages for a session"""
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at).all()
    return messages


@router.post("/{session_id}/end", response_model=schemas.SessionResponse)
def end_session(session_id: UUID, db: Session = Depends(get_db)):
    """End a session"""
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")
    
    session.ended_at = datetime.utcnow()
    db.commit()
    
    logging.log_session_ended(db, session.user_id, session_id)
    
    # Cleanup session memories if in ephemeral mode
    user = db.query(models.User).filter(models.User.user_id == session.user_id).first()
    if user and user.condition_id in ["SESSION_AUTO", "SESSION_USER"]:
        memory_manager.cleanup_session_memories(session_id, db)
    
    return session

