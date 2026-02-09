from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, logging
from uuid import UUID

router = APIRouter(prefix="/condition", tags=["condition"])

CONDITION_DESCRIPTIONS = {
    "SESSION_AUTO": "Your conversation will not be saved after this session ends.",
    "SESSION_USER": "You can review saved memories, but they will be cleared after this session ends.",
    "PERSISTENT_AUTO": "Your conversation is automatically saved and will persist in future sessions.",
    "PERSISTENT_USER": "You can choose which information to save, edit, or delete, and it will persist in future sessions."
}


@router.get("/{user_id}", response_model=schemas.ConditionResponse)
def get_condition(user_id: UUID, db: Session = Depends(get_db)):
    """Get the condition for a user"""
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "condition_id": user.condition_id,
        "description": CONDITION_DESCRIPTIONS.get(user.condition_id, "Unknown condition")
    }


@router.put("/{user_id}")
def update_condition(
    user_id: UUID,
    condition_id: str,
    db: Session = Depends(get_db),
    is_developer: bool = False  # This would be checked via auth in production
):
    """Update user condition (developer/admin only)"""
    valid_conditions = ["SESSION_AUTO", "SESSION_USER", "PERSISTENT_AUTO", "PERSISTENT_USER"]
    if not condition_id or condition_id not in valid_conditions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid condition_id. Must be one of: {', '.join(valid_conditions)}"
        )
    
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_condition = user.condition_id
    user.condition_id = condition_id
    db.commit()
    
    # Log condition change
    if old_condition != condition_id:
        logging.log_condition_changed(db, user_id, condition_id)
    
    return {
        "condition_id": user.condition_id,
        "description": CONDITION_DESCRIPTIONS.get(user.condition_id)
    }

