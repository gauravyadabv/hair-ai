from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import User, Assessment, Photo, ImageAnalysis
from app.api.deps import get_current_user
from app.engine.image_quality import image_quality_engine
from app.engine.feature_extraction import feature_extraction_engine
from app.engine.ml_inference import ml_inference_engine

router = APIRouter(prefix="/assessments", tags=["Image Analysis & Feature Extraction"])

@router.post("/{assessment_id}/analyze")
def run_assessment_image_analysis(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Module D & E Execution:
    1. Loads all acceptable photos for the assessment.
    2. Runs feature extraction (lighting normalization, ROI, pixel segmentation, color analysis).
    3. Evaluates regional comparisons (Phase 3).
    4. Records ImageAnalysis records in the database idempotently.
    """
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    photos = db.query(Photo).filter(Photo.assessment_id == assessment_id).all()
    if not photos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No photos uploaded for this assessment. Please upload photos before analyzing."
        )

    analysis_results = {}
    saved_analyses = []

    for photo in photos:
        if photo.quality_status == "rejected":
            continue

        q_info = image_quality_engine.evaluate_quality(photo.private_file_path, photo.id, photo.angle)
        inf_result = ml_inference_engine.run_inference(
            image_path=photo.private_file_path,
            angle=photo.angle,
            quality_info=q_info
        )

        analysis_results[photo.angle] = inf_result

        # Save record in DB
        existing_analysis = db.query(ImageAnalysis).filter(ImageAnalysis.photo_id == photo.id).first()
        if existing_analysis:
            record = existing_analysis
            record.preprocessing_version = settings.PREPROCESSING_VERSION
            record.model_version = inf_result.get("model_version", settings.DEFAULT_MODEL_VERSION)
            record.feature_data_json = inf_result.get("feature_data")
            record.confidence_data_json = inf_result.get("confidence_data")
            record.analysis_status = "completed"
        else:
            record = ImageAnalysis(
                photo_id=photo.id,
                preprocessing_version=settings.PREPROCESSING_VERSION,
                model_version=inf_result.get("model_version", settings.DEFAULT_MODEL_VERSION),
                analysis_status="completed",
                feature_data_json=inf_result.get("feature_data"),
                confidence_data_json=inf_result.get("confidence_data")
            )
            db.add(record)

        saved_analyses.append(record)

    # Cross-regional comparative analysis
    regional_comparison = feature_extraction_engine.compare_regions(analysis_results)

    assessment.assessment_status = "analyzed"
    db.commit()

    return {
        "assessment_id": assessment_id,
        "status": "completed",
        "photos_analyzed_count": len(saved_analyses),
        "regional_comparison": regional_comparison,
        "analyses": analysis_results
    }

@router.get("/{assessment_id}/analysis")
def get_assessment_image_analysis(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all feature extraction records for the assessment."""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    photos = db.query(Photo).filter(Photo.assessment_id == assessment_id).all()
    photo_ids = [p.id for p in photos]
    analyses = db.query(ImageAnalysis).filter(ImageAnalysis.photo_id.in_(photo_ids)).all() if photo_ids else []

    results = []
    angle_map = {p.id: p.angle for p in photos}
    for a in analyses:
        results.append({
            "id": a.id,
            "photo_id": a.photo_id,
            "angle": angle_map.get(a.photo_id, "unknown"),
            "preprocessing_version": a.preprocessing_version,
            "model_version": a.model_version,
            "analysis_status": a.analysis_status,
            "feature_data": a.feature_data_json,
            "confidence_data": a.confidence_data_json,
            "created_at": a.created_at
        })

    return {
        "assessment_id": assessment_id,
        "analyses": results
    }

