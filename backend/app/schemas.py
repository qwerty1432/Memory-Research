from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# User schemas
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    condition_id: Optional[str] = None  # Optional for admin assignment


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    user_id: UUID
    username: str
    condition_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QualtricsAuthenticateRequest(BaseModel):
    qualtrics_id: str = Field(..., min_length=1, max_length=255)
    # Preferred name going forward (Qualtrics ResponseID). We still accept `qualtrics_id`
    # for backwards compatibility with existing iframe URLs/tests.
    response_id: Optional[str] = Field(None, min_length=1, max_length=255)
    phase: Optional[int] = Field(None, ge=1, le=3)


class QualtricsAuthenticateResponse(BaseModel):
    user_id: UUID
    session_id: UUID
    condition_id: str
    username: str
    phase: Optional[int] = None
    resumed_session: bool = False


# Session schemas
class SessionCreate(BaseModel):
    user_id: UUID


class SessionResponse(BaseModel):
    session_id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Message schemas
class MessageCreate(BaseModel):
    session_id: UUID
    role: str
    content: str


class MessageResponse(BaseModel):
    msg_id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# Memory schemas
class MemoryCreate(BaseModel):
    user_id: UUID
    session_id: Optional[UUID] = None
    text: str = Field(..., max_length=200)
    is_active: bool = False


class MemoryUpdate(BaseModel):
    text: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class MemoryResponse(BaseModel):
    memory_id: UUID
    user_id: UUID
    session_id: Optional[UUID] = None
    text: str
    phase: Optional[int] = None  # 1–3 when set; null for legacy rows
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# Chat schemas
class ChatRequest(BaseModel):
    user_id: UUID
    session_id: UUID
    message: str
    phase: Optional[int] = Field(None, ge=1, le=3)


class PhaseStatus(BaseModel):
    phase: int
    prompts_answered: int
    total_prompts: int
    phase_complete: bool
    study_complete: bool = False
    current_prompt_index: int = 0
    followups_used_for_prompt: int = 0


class AdvancePhaseRequest(BaseModel):
    user_id: UUID
    session_id: UUID


class AdvancePhaseResponse(BaseModel):
    phase_status: PhaseStatus
    opening_message: str


class ChatResponse(BaseModel):
    response: str
    memory_candidates: List[MemoryResponse] = []
    phase_status: Optional[PhaseStatus] = None


# Condition schemas
class ConditionResponse(BaseModel):
    condition_id: str
    description: str


# Event schemas
class EventCreate(BaseModel):
    user_id: Optional[UUID] = None
    type: str
    payload_json: Optional[dict] = None


# Survey schemas
class SurveyQuestion(BaseModel):
    question_id: str
    question_text: str
    question_type: str  # "free_response", "mcq", "rating", "likert", "yes_no"
    options: Optional[List[str]] = None  # For MCQ
    min_rating: Optional[int] = None  # For rating scales
    max_rating: Optional[int] = None
    required: bool = True


class SurveyTemplate(BaseModel):
    survey_type: str  # "mid_checkpoint", "pre", "post"
    questions: List[SurveyQuestion]


class SurveyResponseItem(BaseModel):
    question_id: str
    response_value: dict  # Flexible JSON structure


class SurveySubmission(BaseModel):
    user_id: UUID
    session_id: Optional[UUID] = None  # Session before checkpoint
    survey_type: str
    responses: List[SurveyResponseItem]


class SurveyResponseResponse(BaseModel):
    response_id: UUID
    user_id: UUID
    session_id: Optional[UUID] = None
    survey_type: str
    question_id: str
    question_text: str
    response_type: str
    response_value: dict
    created_at: datetime

    model_config = {"from_attributes": True}

