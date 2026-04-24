from sqlalchemy.orm import Session
from .models import User
from .schemas import UserCreate
import re
import uuid
import hashlib
import base64
import bcrypt
import secrets


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


VALID_CONDITIONS = ["SESSION_AUTO", "PERSISTENT_AUTO", "PERSISTENT_USER"]


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
    if final_condition_id not in VALID_CONDITIONS:
        raise ValueError(f"Invalid condition_id. Must be one of: {', '.join(VALID_CONDITIONS)}")
    
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


def get_user_by_qualtrics_id(db: Session, qualtrics_id: str) -> User | None:
    """Get user by Qualtrics ID"""
    return db.query(User).filter(User.qualtrics_id == qualtrics_id).first()


def assign_condition_round_robin(db: Session) -> str:
    """Assign experimental condition using round-robin rotation"""
    conditions = VALID_CONDITIONS
    
    # Count existing Qualtrics users to determine next condition
    qualtrics_user_count = db.query(User).filter(User.qualtrics_id.isnot(None)).count()
    
    # Round-robin: cycle through conditions based on count
    condition_index = qualtrics_user_count % len(conditions)
    return conditions[condition_index]


def create_qualtrics_user(db: Session, qualtrics_id: str, condition_id: str = None) -> User:
    """Create a new user from Qualtrics ID (no password required)"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.qualtrics_id == qualtrics_id).first()
    if existing_user:
        raise ValueError(f"User with Qualtrics ID {qualtrics_id} already exists")
    
    # Assign condition if not provided (round-robin)
    if condition_id is None:
        condition_id = assign_condition_round_robin(db)
    
    # Validate condition_id
    if condition_id not in VALID_CONDITIONS:
        raise ValueError(f"Invalid condition_id. Must be one of: {', '.join(VALID_CONDITIONS)}")
    
    # Generate username and random password (user won't need to login)
    username = f"qualtrics_{qualtrics_id}"
    # Generate a secure random password (user won't need to know it)
    random_password = secrets.token_urlsafe(32)
    
    user = User(
        user_id=uuid.uuid4(),
        username=username,
        password_hash=get_password_hash(random_password),
        condition_id=condition_id,
        qualtrics_id=qualtrics_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

