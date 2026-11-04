from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import User, Assessment, Photo, QuestionnaireAnswer, ImageAnalysis, Report
from app.schemas.schemas import ReportResponse
from app.api.deps import get_current_user
from app.engine.questionnaire import questionnaire_engine
from app.engine.image_quality import image_quality_engine
from app.engine.assessment import assessment_engine
from app.engine.report import report_engine

router = APIRouter(prefix="/assessments", tags=["Reports & Assessment Engine"])

@router.post("/{assessment_id}/report", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def generate_assessment_report(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Executes Module F (Assessment Engine) and Module G (Report Engine):
    - Synthesizes user questionnaire evidence
    - Synthesizes photo quality metrics
    - Synthesizes image feature extractions
    - Evaluates patterns and recommendations
    - Generates 12-section structured report
    - Compiles portable PDF report
    - Persists report record in MySQL/DB
    """
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    # 1. Gather questionnaire data
    answers = db.query(QuestionnaireAnswer).filter(QuestionnaireAnswer.assessment_id == assessment_id).all()
    raw_answer_list = [{"question_key": a.question_key, "answer_value": a.answer_value} for a in answers]
    q_data = questionnaire_engine.validate_and_process(raw_answer_list, consent_status=True)
    q_data["assessment_id"] = assessment_id

    # 2. Gather photos & quality data
    photos = db.query(Photo).filter(Photo.assessment_id == assessment_id).all()
    photo_quality_data = {}
    image_feature_data = {}

    for p in photos:
        q_info = image_quality_engine.evaluate_quality(p.private_file_path, p.id, p.angle)
        photo_quality_data[p.angle] = q_info

        # Gather image analysis if completed
        analysis = db.query(ImageAnalysis).filter(ImageAnalysis.photo_id == p.id).first()
        if analysis and analysis.feature_data_json:
            image_feature_data[p.angle] = {
                "feature_data": analysis.feature_data_json,
                "confidence_data": analysis.confidence_data_json
            }

    # 3. Run Module F Assessment Engine
    assessment_result = assessment_engine.evaluate(
        questionnaire_data=q_data,
        photo_quality_data=photo_quality_data,
        image_feature_data=image_feature_data
    )

    # 4. Run Module G Report Engine
    structured_report = report_engine.generate_report(
        assessment_id=assessment_id,
        assessment_created_at=assessment.created_at,
        questionnaire_data=q_data,
        photo_quality_data=photo_quality_data,
        image_feature_data=image_feature_data,
        assessment_result=assessment_result
    )

    # 5. Generate PDF report
    pdf_filename = f"report_{assessment_id}.pdf"
    pdf_path = settings.REPORTS_DIR / pdf_filename
    report_engine.generate_pdf_report(structured_report, pdf_path)

    # 6. Save or update Report in DB (idempotent)
    existing_report = db.query(Report).filter(Report.assessment_id == assessment_id).first()
    if existing_report:
        report_record = existing_report
        report_record.report_version = settings.REPORT_VERSION
        report_record.report_data_json = structured_report
        report_record.pdf_file_path = str(pdf_path) if pdf_path.exists() else None
        report_record.generated_at = datetime.now(timezone.utc)
    else:
        report_record = Report(
            assessment_id=assessment_id,
            report_version=settings.REPORT_VERSION,
            report_data_json=structured_report,
            pdf_file_path=str(pdf_path) if pdf_path.exists() else None
        )
        db.add(report_record)

    # Mark assessment completed
    assessment.assessment_status = "completed"
    assessment.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(report_record)

    return ReportResponse(
        id=report_record.id,
        assessment_id=report_record.assessment_id,
        report_version=report_record.report_version,
        generated_at=report_record.generated_at,
        report_data=report_record.report_data_json
    )

@router.get("/{assessment_id}/report", response_model=ReportResponse)
def get_assessment_report(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves the stored report for a completed assessment."""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    report = db.query(Report).filter(Report.assessment_id == assessment_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report has not yet been generated for this assessment.")

    return ReportResponse(
        id=report.id,
        assessment_id=report.assessment_id,
        report_version=report.report_version,
        generated_at=report.generated_at,
        report_data=report.report_data_json
    )

@router.get("/{assessment_id}/report/pdf")
def download_pdf_report(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Downloads the generated PDF report."""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    report = db.query(Report).filter(Report.assessment_id == assessment_id).first()
    if not report or not report.pdf_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF report not found.")

    path = Path(report.pdf_file_path)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file does not exist on disk.")

    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=f"hair_health_report_{assessment_id[:8]}.pdf"
    )

