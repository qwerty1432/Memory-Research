"""
Survey question templates for different survey types.
These can be moved to a database later for easier updates.
"""
from typing import List
from .schemas import SurveyQuestion, SurveyTemplate


def get_mid_checkpoint_template() -> SurveyTemplate:
    """Get the mid-conversation checkpoint survey template."""
    questions: List[SurveyQuestion] = [
        # Trust Measurement
        SurveyQuestion(
            question_id="trust_1",
            question_text="How much do you trust this AI companion?",
            question_type="rating",
            min_rating=1,
            max_rating=7,
            required=True
        ),
        SurveyQuestion(
            question_id="trust_2",
            question_text="How reliable do you find the AI's responses?",
            question_type="rating",
            min_rating=1,
            max_rating=7,
            required=True
        ),
        
        # Privacy Perception
        SurveyQuestion(
            question_id="privacy_1",
            question_text="I feel my privacy is respected",
            question_type="likert",
            options=["Strongly Disagree", "Disagree", "Somewhat Disagree", "Neutral", "Somewhat Agree", "Agree", "Strongly Agree"],
            required=True
        ),
        SurveyQuestion(
            question_id="privacy_2",
            question_text="I am comfortable sharing information with this AI",
            question_type="likert",
            options=["Strongly Disagree", "Disagree", "Somewhat Disagree", "Neutral", "Somewhat Agree", "Agree", "Strongly Agree"],
            required=True
        ),
        
        # Disclosure Patterns
        SurveyQuestion(
            question_id="disclosure_1",
            question_text="What information have you shared so far?",
            question_type="free_response",
            required=True
        ),
        SurveyQuestion(
            question_id="disclosure_2",
            question_text="What topics have you discussed?",
            question_type="free_response",
            required=True
        ),
        
        # Satisfaction
        SurveyQuestion(
            question_id="satisfaction_1",
            question_text="How satisfied are you with the conversation?",
            question_type="rating",
            min_rating=1,
            max_rating=5,
            required=True
        ),
        SurveyQuestion(
            question_id="satisfaction_2",
            question_text="How helpful has the AI been?",
            question_type="rating",
            min_rating=1,
            max_rating=5,
            required=True
        ),
        
        # Memory Awareness
        SurveyQuestion(
            question_id="memory_1",
            question_text="Do you think the AI remembers information from earlier in the conversation?",
            question_type="yes_no",
            required=True
        ),
        SurveyQuestion(
            question_id="memory_2",
            question_text="Have you noticed the AI referencing previous conversations or information you shared?",
            question_type="yes_no",
            required=True
        ),
    ]
    
    return SurveyTemplate(
        survey_type="mid_checkpoint",
        questions=questions
    )


def get_survey_template(survey_type: str) -> SurveyTemplate:
    """Get survey template by type."""
    if survey_type == "mid_checkpoint":
        return get_mid_checkpoint_template()
    else:
        # Return empty template for other types (to be implemented later)
        return SurveyTemplate(
            survey_type=survey_type,
            questions=[]
        )
