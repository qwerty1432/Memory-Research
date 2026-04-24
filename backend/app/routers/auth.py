from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..database import get_db
from .. import auth, schemas, models, logging, prompt_builder
from ..models import Session as SessionModel
from ..models import Message
from uuid import UUID, uuid4
from datetime import datetime
import random

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBasic()
QUALTRICS_PHASE_EVENT = "qualtrics_phase_session"


def _build_phase_prompt_orders(phase: int) -> dict[str, list[int]]:
    prompts = prompt_builder.get_phase_prompts(phase)
    order = list(range(len(prompts)))
    random.shuffle(order)
    return {str(phase): order}


def _opening_for_phase_with_order(phase: int, orders: dict[str, list[int]]) -> str:
    prompts = prompt_builder.get_phase_prompts(phase)
    order = orders.get(str(phase), [])
    if not prompts or not order or len(order) != len(prompts):
        return prompt_builder.get_phase_opening_message(phase)
    return prompt_builder.get_phase_opening_message_for_question(phase, prompts[order[0]])


def _extract_session_phase_map(db: Session, user_id: UUID) -> dict[str, int]:
    events = (
        db.query(models.Event)
        .filter(
            models.Event.user_id == user_id,
            models.Event.type == QUALTRICS_PHASE_EVENT,
        )
        .order_by(models.Event.created_at.asc())
        .all()
    )
    session_phase_map: dict[str, int] = {}
    for event in events:
        payload = event.payload_json or {}
        session_id = payload.get("session_id")
        phase = payload.get("phase")
        if not session_id:
            continue
        try:
            phase_int = int(phase)
        except (TypeError, ValueError):
            continue
        if phase_int not in (1, 2, 3):
            continue
        session_phase_map[str(session_id)] = phase_int
    return session_phase_map


def _find_active_session_for_phase(db: Session, user_id: UUID, phase: int) -> SessionModel | None:
    active_sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == user_id,
            SessionModel.ended_at == None,
        )
        .order_by(SessionModel.started_at.desc())
        .all()
    )
    session_phase_map = _extract_session_phase_map(db, user_id)
    for active in active_sessions:
        if session_phase_map.get(str(active.session_id)) == phase:
            return active
    return None


def _tag_session_with_phase(db: Session, user_id: UUID, session_id: UUID, phase: int):
    logging.log_event(
        db,
        QUALTRICS_PHASE_EVENT,
        user_id,
        {"session_id": str(session_id), "phase": phase},
    )


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    try:
        # Default condition if not provided (can be changed by admin)
        condition_id = user_data.condition_id or "SESSION_AUTO"
        user = auth.create_user(db, user_data, condition_id)
        
        # Log condition assignment
        logging.log_condition_assigned(db, user.user_id, user.condition_id)
        
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=schemas.UserResponse)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """Login and return user info"""
    user = auth.authenticate_user(db, credentials.username, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    return user


@router.get("/user/{user_id}", response_model=schemas.UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = auth.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/qualtrics/authenticate", response_model=schemas.QualtricsAuthenticateResponse)
def qualtrics_authenticate(
    request: schemas.QualtricsAuthenticateRequest,
    db: Session = Depends(get_db)
):
    """Authenticate or create user from Qualtrics Response ID"""
    # Treat Qualtrics ResponseID as the canonical participant identifier.
    # We accept both `response_id` (preferred) and `qualtrics_id` (legacy) for compatibility.
    qualtrics_id = request.response_id or request.qualtrics_id
    
    # Check if user exists
    user = auth.get_user_by_qualtrics_id(db, qualtrics_id)
    
    if not user:
        # Create new user
        try:
            user = auth.create_qualtrics_user(db, qualtrics_id)
            # Log condition assignment
            logging.log_condition_assigned(db, user.user_id, user.condition_id)
        except IntegrityError:
            # Race condition guard: parallel authenticate calls may both try to create
            # the same Qualtrics user. Roll back and fetch the existing row.
            db.rollback()
            user = auth.get_user_by_qualtrics_id(db, qualtrics_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create or fetch Qualtrics user"
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    phase = request.phase
    resumed_session = False
    new_session = None

    active_sessions = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == user.user_id,
            SessionModel.ended_at == None
        )
        .all()
    )

    # Single-block mode: if phase is None, check for existing progress and resume
    # or initialize at phase 1. If phase is provided (legacy), use phase-specific logic.
    if phase is None:
        # Single-block mode: find any active session and check its progress
        if active_sessions:
            # Use the most recent active session
            new_session = active_sessions[0]
            resumed_session = True
            
            # Check if there's existing progress
            progress = logging.get_latest_progress(db, user.user_id, new_session.session_id)
            if progress:
                # Resume from saved progress
                phase = progress.get("current_phase", 1)
            else:
                # No progress found, initialize at phase 1
                phase = 1
                phase_prompt_orders = _build_phase_prompt_orders(1)
                # Initialize progress state
                logging.log_progress_update(
                    db,
                    user.user_id,
                    new_session.session_id,
                    current_phase=1,
                    current_prompt_index=0,
                    followups_used_for_prompt=0,
                    used_followups_for_prompt=[],
                    phase_complete=False,
                    study_complete=False,
                    phase_prompt_orders=phase_prompt_orders,
                )
                # Add phase opening message if session is empty
                assistant_count = (
                    db.query(Message)
                    .filter(
                        Message.session_id == new_session.session_id,
                        Message.role == "assistant",
                    )
                    .count()
                )
                if assistant_count == 0:
                    phase_opening = Message(
                        session_id=new_session.session_id,
                        role="assistant",
                        content=_opening_for_phase_with_order(1, phase_prompt_orders),
                    )
                    db.add(phase_opening)
                    db.commit()
                    logging.log_message_received(
                        db, user.user_id, new_session.session_id, phase_opening.content
                    )
        else:
            # No active session, create new one at phase 1
            phase = 1
            new_session = SessionModel(
                session_id=uuid4(),
                user_id=user.user_id
            )
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            logging.log_session_started(db, user.user_id, new_session.session_id)
            phase_prompt_orders = _build_phase_prompt_orders(1)
            
            # Initialize progress state
            logging.log_progress_update(
                db,
                user.user_id,
                new_session.session_id,
                current_phase=1,
                current_prompt_index=0,
                followups_used_for_prompt=0,
                used_followups_for_prompt=[],
                phase_complete=False,
                study_complete=False,
                phase_prompt_orders=phase_prompt_orders,
            )
            
            # Add phase opening message
            phase_opening = Message(
                session_id=new_session.session_id,
                role="assistant",
                content=_opening_for_phase_with_order(1, phase_prompt_orders),
            )
            db.add(phase_opening)
            db.commit()
            logging.log_message_received(db, user.user_id, new_session.session_id, phase_opening.content)
    else:
        # Legacy phase-specific mode: resume same-phase active session if present
        same_phase_session = _find_active_session_for_phase(db, user.user_id, phase)
        if same_phase_session:
            resumed_session = True
            new_session = same_phase_session
            assistant_count = (
                db.query(Message)
                .filter(
                    Message.session_id == new_session.session_id,
                    Message.role == "assistant",
                )
                .count()
            )
            if assistant_count == 0:
                phase_opening = Message(
                    session_id=new_session.session_id,
                    role="assistant",
                    content=prompt_builder.get_phase_opening_message(phase),
                )
                db.add(phase_opening)
                db.commit()
                logging.log_message_received(
                    db, user.user_id, new_session.session_id, phase_opening.content
                )

    # End other active sessions (keep resumed session open if present).
    for active in active_sessions:
        if new_session and active.session_id == new_session.session_id:
            continue
        active.ended_at = datetime.utcnow()
        db.commit()
        logging.log_session_ended(db, user.user_id, active.session_id)

    if not new_session:
        # Create new session (legacy phase-specific mode)
        new_session = SessionModel(
            session_id=uuid4(),
            user_id=user.user_id
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # Log session started
        logging.log_session_started(db, user.user_id, new_session.session_id)
        if phase is not None:
            _tag_session_with_phase(db, user.user_id, new_session.session_id, phase)
            phase_opening = Message(
                session_id=new_session.session_id,
                role="assistant",
                content=prompt_builder.get_phase_opening_message(phase),
            )
            db.add(phase_opening)
            db.commit()
            logging.log_message_received(db, user.user_id, new_session.session_id, phase_opening.content)

    # Log the Qualtrics linkage explicitly for analysis/debugging
    logging.log_event(
        db,
        "qualtrics_authenticated",
        user.user_id,
        {
            "session_id": str(new_session.session_id),
            "qualtrics_response_id": qualtrics_id,
            "phase": phase,
            "resumed_session": resumed_session,
        },
    )
    
    return schemas.QualtricsAuthenticateResponse(
        user_id=user.user_id,
        session_id=new_session.session_id,
        condition_id=user.condition_id,
        username=user.username,
        phase=phase,
        resumed_session=resumed_session,
    )

