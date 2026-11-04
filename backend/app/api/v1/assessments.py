from typing import List, Dict, Any
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import User, Assessment, QuestionnaireAnswer, Photo
from app.schemas.schemas import (
    AssessmentResponse,
    QuestionnaireSubmit,
    QuestionnaireValidationResult
)
from app.api.deps import get_current_user
from app.engine.questionnaire import questionnaire_engine

router = APIRouter(prefix="/assessments", tags=["Assessments & Questionnaire"])

@router.get("/questionnaire/schema")
def get_questionnaire_schema():
    """Returns the full specification of questions for the frontend questionnaire engine."""
    return questionnaire_engine.get_specification()

@router.post("", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
def create_assessment(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Initializes a new assessment session for the authenticated user."""
    assessment = Assessment(
        user_id=current_user.id,
        assessment_status="pending",
        questionnaire_version=settings.QUESTIONNAIRE_VERSION,
        engine_version=settings.ENGINE_VERSION
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment

@router.get("", response_model=List[AssessmentResponse])
def list_user_assessments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all assessments belonging to the logged-in user."""
    assessments = db.query(Assessment).filter(Assessment.user_id == current_user.id).order_by(Assessment.created_at.desc()).all()
    return assessments

@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves details of a specific assessment."""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")
    return assessment

@router.post("/{assessment_id}/answers")
def submit_questionnaire_answers(
    assessment_id: str,
    payload: QuestionnaireSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Submits user answers for Module A.
    Validates completeness and categorizes results.
    """
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    raw_items = [{"question_key": item.question_key, "answer_value": item.answer_value} for item in payload.answers]
    processed = questionnaire_engine.validate_and_process(raw_items, consent_status=payload.consent_confirmed)

    # Save or update answers in DB
    # Remove previous answers for idempotency
    db.query(QuestionnaireAnswer).filter(QuestionnaireAnswer.assessment_id == assessment_id).delete()

    for item in payload.answers:
        val_str = json.dumps(item.answer_value) if not isinstance(item.answer_value, str) else item.answer_value
        ans = QuestionnaireAnswer(
            assessment_id=assessment_id,
            question_key=item.question_key,
            answer_value=val_str
        )
        db.add(ans)

    if processed["is_complete"]:
        assessment.assessment_status = "questionnaire_completed"
    else:
        assessment.assessment_status = "questionnaire_partial"

    db.commit()

    return {
        "assessment_id": assessment_id,
        "is_complete": processed["is_complete"],
        "missing_required_fields": processed["missing_required_fields"],
        "categorized": processed["categorized"],
        "message": "Questionnaire answers successfully recorded."
    }

