from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models
from ..survey_templates import get_survey_template
from uuid import UUID
from typing import List

router = APIRouter(prefix="/survey", tags=["survey"])


@router.get("/template/{survey_type}", response_model=schemas.SurveyTemplate)
def get_survey_template_endpoint(survey_type: str):
    """Get survey question template by type."""
    template = get_survey_template(survey_type)
    return template


@router.post("/submit", status_code=201)
def submit_survey(
    submission: schemas.SurveySubmission,
    db: Session = Depends(get_db)
):
    """Submit survey responses."""
    # Verify user exists
    user = db.query(models.User).filter(models.User.user_id == submission.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify session exists if provided
    if submission.session_id:
        session = db.query(models.Session).filter(
            models.Session.session_id == submission.session_id
        ).first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    
    # Get the survey template to validate questions
    template = get_survey_template(submission.survey_type)
    template_question_ids = {q.question_id for q in template.questions}
    
    # Create survey response records
    created_responses = []
    for response_item in submission.responses:
        # Find the question in template to get metadata
        question = next(
            (q for q in template.questions if q.question_id == response_item.question_id),
            None
        )
        
        if not question:
            raise HTTPException(
                status_code=400,
                detail=f"Question ID {response_item.question_id} not found in template"
            )
        
        # Create response record
        survey_response = models.SurveyResponse(
            user_id=submission.user_id,
            session_id=submission.session_id,
            survey_type=submission.survey_type,
            question_id=response_item.question_id,
            question_text=question.question_text,
            response_type=question.question_type,
            response_value=response_item.response_value
        )
        db.add(survey_response)
        created_responses.append(survey_response)
    
    db.commit()
    
    # Refresh to get IDs
    for response in created_responses:
        db.refresh(response)
    
    return {
        "message": "Survey submitted successfully",
        "response_count": len(created_responses),
        "responses": [schemas.SurveyResponseResponse.model_validate(r) for r in created_responses]
    }


@router.get("/{user_id}/responses", response_model=List[schemas.SurveyResponseResponse])
def get_user_responses(
    user_id: UUID,
    survey_type: str = None,
    db: Session = Depends(get_db)
):
    """Get all survey responses for a user, optionally filtered by survey type."""
    query = db.query(models.SurveyResponse).filter(
        models.SurveyResponse.user_id == user_id
    )
    
    if survey_type:
        query = query.filter(models.SurveyResponse.survey_type == survey_type)
    
    responses = query.order_by(models.SurveyResponse.created_at.desc()).all()
    return [schemas.SurveyResponseResponse.model_validate(r) for r in responses]
