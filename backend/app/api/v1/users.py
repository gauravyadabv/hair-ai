from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, Assessment, Photo, QuestionnaireAnswer, ImageAnalysis, Report, ConsentRecord
from app.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Account Privacy & Data Rights"])

@router.get("/me/data")
def export_my_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Data Privacy & Portability:
    Exports all personal information, questionnaire answers, photo metadata, analyses, reports,
    and consent records associated with the authenticated account.
    """
    assessments = db.query(Assessment).filter(Assessment.user_id == current_user.id).all()
    consents = db.query(ConsentRecord).filter(ConsentRecord.user_id == current_user.id).all()

    assessments_data = []
    for a in assessments:
        answers = db.query(QuestionnaireAnswer).filter(QuestionnaireAnswer.assessment_id == a.id).all()
        photos = db.query(Photo).filter(Photo.assessment_id == a.id).all()
        reports = db.query(Report).filter(Report.assessment_id == a.id).all()

        assessments_data.append({
            "assessment_id": a.id,
            "status": a.assessment_status,
            "created_at": a.created_at,
            "completed_at": a.completed_at,
            "answers": [{ans.question_key: ans.answer_value} for ans in answers],
            "photos_metadata": [{
                "angle": p.angle,
                "width": p.width,
                "height": p.height,
                "uploaded_at": p.uploaded_at,
                "file_hash": p.file_hash,
                "quality_status": p.quality_status
            } for p in photos],
            "reports": [r.report_data_json for r in reports]
        })

    return {
        "user_profile": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "created_at": current_user.created_at
        },
        "consent_history": [{
            "type": c.consent_type,
            "version": c.consent_version,
            "accepted": c.accepted,
            "accepted_at": c.accepted_at
        } for c in consents],
        "assessments": assessments_data
    }

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    GDPR & Right to be Forgotten:
    Permanently deletes user account, deletes all private photo files and PDF reports on disk,
    and cascades database deletions.
    """
    # Find all photos and remove files from disk
    assessments = db.query(Assessment).filter(Assessment.user_id == current_user.id).all()
    for a in assessments:
        photos = db.query(Photo).filter(Photo.assessment_id == a.id).all()
        for p in photos:
            try:
                p_file = Path(p.private_file_path)
                if p_file.exists():
                    p_file.unlink()
            except Exception:
                pass

        reports = db.query(Report).filter(Report.assessment_id == a.id).all()
        for r in reports:
            if r.pdf_file_path:
                try:
                    r_file = Path(r.pdf_file_path)
                    if r_file.exists():
                        r_file.unlink()
                except Exception:
                    pass

    # Delete user record (cascades in DB)
    db.delete(current_user)
    db.commit()
    return None

