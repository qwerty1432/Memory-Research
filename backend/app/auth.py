from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate
import re
import uuid
import hashlib
import base64
import bcrypt


def _prepare_password(password: str) -> bytes:
    """Prepare password for bcrypt by hashing with SHA256 and base64 encoding"""
    # Hash with SHA256 first to handle passwords longer than 72 bytes
    # Use base64 encoding to keep it compact (32 bytes -> 44 base64 bytes, well under 72)
    password_bytes = password.encode('utf-8')
    # Get SHA256 digest (32 bytes)
    sha256_hash = hashlib.sha256(password_bytes).digest()
    # Base64 encode to get 44 bytes (well under 72 byte limit)
    password_hash_bytes = base64.b64encode(sha256_hash)
    # Ensure it's under 72 bytes (should be 44, but truncate if needed as safety)
    if len(password_hash_bytes) > 72:
        password_hash_bytes = password_hash_bytes[:72]
    return password_hash_bytes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Prepare the password the same way we hashed it (as bytes)
    password_hash_bytes = _prepare_password(plain_password)
    # Use bcrypt directly to verify
    try:
        return bcrypt.checkpw(password_hash_bytes, hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password - handles passwords longer than 72 bytes by hashing with SHA256 first"""
    # Prepare password before passing to bcrypt (as bytes, max 72 bytes)
    password_hash_bytes = _prepare_password(password)
    # Use bcrypt directly to hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_hash_bytes, salt)
    return hashed.decode('utf-8')


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password meets requirements: min 8 chars, at least one number and one letter"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""


def create_user(db: Session, user_data: UserCreate, condition_id: str = "SESSION_AUTO") -> User:
    """Create a new user"""
    # Validate password
    is_valid, error_msg = validate_password(user_data.password)
    if not is_valid:
        raise ValueError(error_msg)
    
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise ValueError("Username already exists")
    
    # Use provided condition_id or default
    final_condition_id = user_data.condition_id or condition_id
    
    # Validate condition_id
    valid_conditions = ["SESSION_AUTO", "SESSION_USER", "PERSISTENT_AUTO", "PERSISTENT_USER"]
    if final_condition_id not in valid_conditions:
        raise ValueError(f"Invalid condition_id. Must be one of: {', '.join(valid_conditions)}")
    
    user = User(
        user_id=uuid.uuid4(),
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        condition_id=final_condition_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    """Authenticate a user"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    """Get user by ID"""
    return db.query(User).filter(User.user_id == user_id).first()

