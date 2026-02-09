from sqlalchemy.orm import Session
from sqlalchemy import desc
from .models import Memory, Session as SessionModel, Message
from typing import List, Optional
from uuid import UUID


def _ensure_uuid(value: Optional[UUID]) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def get_context(user_id: UUID, session_id: UUID, condition: str, db: Session) -> str:
    """
    Get context based on condition:
    - SESSION_AUTO: Recent messages from current session
    - SESSION_USER: User-approved temporary memories from current session
    - PERSISTENT_AUTO: All active memories for user
    - PERSISTENT_USER: User-approved persistent memories
    """
    normalized_user_id = _ensure_uuid(user_id)
    normalized_session_id = _ensure_uuid(session_id)

    context_parts = []
    
    if condition == "SESSION_AUTO":
        # Get recent messages from current session (last 10)
        messages = db.query(Message).filter(
            Message.session_id == normalized_session_id
        ).order_by(desc(Message.created_at)).limit(10).all()
        messages.reverse()  # Oldest first
        
        for msg in messages:
            context_parts.append(f"{msg.role.capitalize()}: {msg.content}")
    
    elif condition == "SESSION_USER":
        # Get user-approved memories from current session
        memories = db.query(Memory).filter(
            Memory.user_id == normalized_user_id,
            Memory.session_id == normalized_session_id,
            Memory.is_active == True
        ).order_by(desc(Memory.created_at)).limit(20).all()
        
        for memory in memories:
            context_parts.append(f"Memory: {memory.text}")
        
        # Also include recent messages
        messages = db.query(Message).filter(
            Message.session_id == normalized_session_id
        ).order_by(desc(Message.created_at)).limit(5).all()
        messages.reverse()
        
        for msg in messages:
            context_parts.append(f"{msg.role.capitalize()}: {msg.content}")
    
    elif condition == "PERSISTENT_AUTO":
        # Get all active memories for user
        memories = db.query(Memory).filter(
            Memory.user_id == normalized_user_id,
            Memory.is_active == True
        ).order_by(desc(Memory.created_at)).limit(20).all()
        
        for memory in memories:
            context_parts.append(f"Memory: {memory.text}")
        
        # Include recent messages from current session
        messages = db.query(Message).filter(
            Message.session_id == normalized_session_id
        ).order_by(desc(Message.created_at)).limit(5).all()
        messages.reverse()
        
        for msg in messages:
            context_parts.append(f"{msg.role.capitalize()}: {msg.content}")
    
    elif condition == "PERSISTENT_USER":
        # Get user-approved persistent memories
        memories = db.query(Memory).filter(
            Memory.user_id == normalized_user_id,
            Memory.is_active == True
        ).order_by(desc(Memory.created_at)).limit(20).all()
        
        for memory in memories:
            context_parts.append(f"Memory: {memory.text}")
        
        # Include recent messages from current session
        messages = db.query(Message).filter(
            Message.session_id == normalized_session_id
        ).order_by(desc(Message.created_at)).limit(5).all()
        messages.reverse()
        
        for msg in messages:
            context_parts.append(f"{msg.role.capitalize()}: {msg.content}")
    
    # Limit total context size (approximately 1000 chars for memories, 6000 total)
    context_text = "\n".join(context_parts)
    if len(context_text) > 6000:
        # Truncate while preserving structure
        lines = context_parts
        truncated = []
        char_count = 0
        for line in lines:
            if char_count + len(line) > 6000:
                break
            truncated.append(line)
            char_count += len(line) + 1  # +1 for newline
        context_text = "\n".join(truncated)
    
    return context_text


def get_all_existing_memories(user_id: UUID, session_id: Optional[UUID], db: Session) -> List[str]:
    """
    Get all existing memory texts (both active and inactive) for deduplication.
    Returns list of memory text strings.
    """
    normalized_user_id = _ensure_uuid(user_id)
    normalized_session_id = _ensure_uuid(session_id)
    
    # For session modes, check only within current session
    # For persistent modes, check across all user memories
    if normalized_session_id:
        memories = db.query(Memory).filter(
            Memory.user_id == normalized_user_id,
            Memory.session_id == normalized_session_id
        ).all()
    else:
        memories = db.query(Memory).filter(
            Memory.user_id == normalized_user_id
        ).all()
    
    return [memory.text for memory in memories]


def get_memory_candidates(user_id: UUID, session_id: UUID, db: Session) -> List[Memory]:
    """Get inactive memory candidates for the current session"""
    normalized_user_id = _ensure_uuid(user_id)
    normalized_session_id = _ensure_uuid(session_id)

    return db.query(Memory).filter(
        Memory.user_id == normalized_user_id,
        Memory.session_id == normalized_session_id,
        Memory.is_active == False
    ).order_by(desc(Memory.created_at)).all()


def _normalize_memory_text(text: str) -> str:
    """Normalize memory text for comparison (lowercase, strip whitespace, remove 'User' prefix)"""
    text = text.strip().lower()
    # Remove "User" prefix if present
    if text.startswith("user"):
        text = text[4:].strip()
    # Normalize whitespace
    return " ".join(text.split())


def check_memory_duplicate(
    new_memory_text: str,
    user_id: UUID,
    session_id: Optional[UUID],
    db: Session
) -> bool:
    """
    Check if a memory is a duplicate of an existing memory.
    Uses simple exact match after normalization.
    
    Returns True if duplicate exists, False otherwise.
    """
    normalized_user_id = _ensure_uuid(user_id)
    normalized_session_id = _ensure_uuid(session_id)
    
    # Normalize the new memory text
    normalized_new = _normalize_memory_text(new_memory_text)
    
    # Get all existing memories (both active and inactive)
    # For session modes, check only within current session
    # For persistent modes, check across all user memories
    if normalized_session_id:
        # Session mode: check only within this session
        existing_memories = db.query(Memory).filter(
            Memory.user_id == normalized_user_id,
            Memory.session_id == normalized_session_id
        ).all()
    else:
        # Persistent mode: check across all user memories
        existing_memories = db.query(Memory).filter(
            Memory.user_id == normalized_user_id
        ).all()
    
    # Check for exact match
    for existing_memory in existing_memories:
        normalized_existing = _normalize_memory_text(existing_memory.text)
        if normalized_new == normalized_existing:
            return True
    
    return False


def create_memory_candidate(
    user_id: UUID,
    session_id: Optional[UUID],
    text: str,
    db: Session
) -> Memory:
    """Create a new memory candidate (inactive by default)"""
    normalized_user_id = _ensure_uuid(user_id)
    normalized_session_id = _ensure_uuid(session_id)

    memory = Memory(
        user_id=normalized_user_id,
        session_id=normalized_session_id,
        text=text[:200],  # Enforce 200 char limit
        is_active=False
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def approve_memory(memory_id: UUID, db: Session) -> Memory:
    """Approve a memory candidate (set is_active=True)"""
    memory = db.query(Memory).filter(Memory.memory_id == memory_id).first()
    if memory:
        memory.is_active = True
        db.commit()
        db.refresh(memory)
    return memory


def delete_memory(memory_id: UUID, db: Session) -> bool:
    """Delete a memory"""
    memory = db.query(Memory).filter(Memory.memory_id == memory_id).first()
    if memory:
        db.delete(memory)
        db.commit()
        return True
    return False


def update_memory(memory_id: UUID, text: Optional[str], is_active: Optional[bool], db: Session) -> Memory:
    """Update a memory"""
    memory = db.query(Memory).filter(Memory.memory_id == memory_id).first()
    if memory:
        if text is not None:
            memory.text = text[:200]  # Enforce 200 char limit
        if is_active is not None:
            memory.is_active = is_active
        db.commit()
        db.refresh(memory)
    return memory


def cleanup_session_memories(session_id: UUID, db: Session):
    """Delete all memories associated with a session (for ephemeral modes)"""
    normalized_session_id = _ensure_uuid(session_id)
    db.query(Memory).filter(Memory.session_id == normalized_session_id).delete()
    db.commit()

