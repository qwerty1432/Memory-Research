from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, memory_manager, logging
from ..models import Memory
from uuid import UUID
from typing import List

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/{user_id}", response_model=List[schemas.MemoryResponse])
def get_memories(user_id: UUID, session_id: UUID = None, db: Session = Depends(get_db)):
    """Get all memories for a user, optionally filtered by session"""
    query = db.query(Memory).filter(Memory.user_id == user_id)
    
    if session_id:
        query = query.filter(Memory.session_id == session_id)
    
    memories = query.order_by(Memory.created_at.desc()).all()
    return memories


@router.get("/candidates/{user_id}/{session_id}", response_model=List[schemas.MemoryResponse])
def get_memory_candidates(user_id: UUID, session_id: UUID, db: Session = Depends(get_db)):
    """Get inactive memory candidates for a session"""
    candidates = memory_manager.get_memory_candidates(user_id, session_id, db)
    return candidates


@router.post("", response_model=schemas.MemoryResponse, status_code=201)
def create_memory(memory_data: schemas.MemoryCreate, db: Session = Depends(get_db)):
    """Create a new memory candidate"""
    memory = memory_manager.create_memory_candidate(
        memory_data.user_id,
        memory_data.session_id,
        memory_data.text,
        db
    )
    logging.log_memory_created(db, memory_data.user_id, memory.memory_id)
    return memory


@router.put("/{memory_id}", response_model=schemas.MemoryResponse)
def update_memory(
    memory_id: UUID,
    memory_update: schemas.MemoryUpdate,
    db: Session = Depends(get_db)
):
    """Update a memory (text or approval status)"""
    memory = memory_manager.update_memory(
        memory_id,
        memory_update.text,
        memory_update.is_active,
        db
    )
    
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    # Log appropriate event
    if memory_update.is_active is True:
        logging.log_memory_approved(db, memory.user_id, memory_id)
    elif memory_update.is_active is False:
        logging.log_memory_rejected(db, memory.user_id, memory_id)
    
    if memory_update.text is not None:
        logging.log_memory_edited(db, memory.user_id, memory_id)
    
    return memory


@router.post("/{memory_id}/approve", response_model=schemas.MemoryResponse)
def approve_memory(memory_id: UUID, db: Session = Depends(get_db)):
    """Approve a memory candidate"""
    memory = memory_manager.approve_memory(memory_id, db)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    logging.log_memory_approved(db, memory.user_id, memory_id)
    return memory


@router.delete("/{memory_id}", status_code=204)
def delete_memory(memory_id: UUID, db: Session = Depends(get_db)):
    """Delete a memory"""
    # Get memory first to log event
    memory = db.query(Memory).filter(Memory.memory_id == memory_id).first()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    user_id = memory.user_id
    success = memory_manager.delete_memory(memory_id, db)
    
    if success:
        logging.log_memory_deleted(db, user_id, memory_id)
    else:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    return None


@router.post("/batch-update")
def batch_update_memories(
    updates: List[dict],  # List of {memory_id, text?, is_active?}
    db: Session = Depends(get_db)
):
    """Batch update multiple memories"""
    results = []
    for update in updates:
        memory_id = UUID(update["memory_id"])
        memory = memory_manager.update_memory(
            memory_id,
            update.get("text"),
            update.get("is_active"),
            db
        )
        if memory:
            results.append(memory)
            # Log events
            if update.get("is_active") is True:
                logging.log_memory_approved(db, memory.user_id, memory_id)
            elif update.get("is_active") is False:
                logging.log_memory_rejected(db, memory.user_id, memory_id)
            if "text" in update:
                logging.log_memory_edited(db, memory.user_id, memory_id)
    
    return {"updated": len(results), "memories": [schemas.MemoryResponse.model_validate(m) for m in results]}

