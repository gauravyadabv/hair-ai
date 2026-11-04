import hashlib
import io
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from PIL import Image
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.models import User, Assessment, Photo
from app.schemas.schemas import PhotoResponse
from app.api.deps import get_current_user
from app.engine.image_quality import image_quality_engine

router = APIRouter(tags=["Photos & Image Quality"])

ALLOWED_ANGLES = ["front_hairline", "top_scalp", "crown", "left_temple", "right_temple"]

@router.post("/assessments/{assessment_id}/photos", response_model=PhotoResponse, status_code=status.HTTP_201_CREATED)
async def upload_assessment_photo(
    assessment_id: str,
    angle: str = Form(..., description="Angle: front_hairline, top_scalp, crown, left_temple, right_temple"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Module B & C Pipeline:
    1. Validates angle against required 5 angles.
    2. Validates content-type and size.
    3. Strips EXIF metadata & corrects orientation.
    4. Computes SHA256 file hash and saves to private storage.
    5. Runs Image Quality Engine (blur, brightness, contrast, resolution).
    6. Stores photo record in DB.
    """
    if angle not in ALLOWED_ANGLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid angle '{angle}'. Must be one of: {', '.join(ALLOWED_ANGLES)}"
        )

    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    # Read bytes and check size
    contents = await file.read()
    if len(contents) > settings.MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size exceeds the maximum allowed limit of {settings.MAX_IMAGE_SIZE_BYTES // (1024*1024)} MB."
        )

    # Validate image decoding & strip EXIF
    try:
        pil_img = Image.open(io.BytesIO(contents))
        pil_img.verify()  # verify integrity
        # Re-open because verify() closes the file pointer
        pil_img = Image.open(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file is corrupted or not a valid image: {str(e)}"
        )

    # Remove EXIF metadata and fix orientation
    clean_img = image_quality_engine.check_and_correct_orientation(pil_img)
    width, height = clean_img.size

    # Check minimum dimensions
    if width < settings.MIN_IMAGE_DIMENSION or height < settings.MIN_IMAGE_DIMENSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image resolution {width}x{height} is below minimum {settings.MIN_IMAGE_DIMENSION}x{settings.MIN_IMAGE_DIMENSION} pixels."
        )

    # Compute SHA256 hash
    file_hash = hashlib.sha256(contents).hexdigest()

    # Save to private storage with secure filename
    filename = f"{assessment_id}_{angle}_{file_hash[:12]}.jpg"
    private_path = settings.PHOTOS_DIR / filename

    # Save cleanly as JPEG without EXIF
    if clean_img.mode in ("RGBA", "P"):
        clean_img = clean_img.convert("RGB")
    clean_img.save(str(private_path), format="JPEG", quality=95)

    # Check if a photo for this angle already exists for this assessment; replace if so (idempotent)
    existing_photo = db.query(Photo).filter(
        Photo.assessment_id == assessment_id,
        Photo.angle == angle
    ).first()

    if existing_photo:
        # Delete old file
        old_file = Path(existing_photo.private_file_path)
        if old_file.exists() and old_file != private_path:
            try:
                old_file.unlink()
            except Exception:
                pass
        photo_record = existing_photo
        photo_record.private_file_path = str(private_path)
        photo_record.file_hash = file_hash
        photo_record.width = width
        photo_record.height = height
    else:
        photo_record = Photo(
            assessment_id=assessment_id,
            angle=angle,
            private_file_path=str(private_path),
            file_hash=file_hash,
            width=width,
            height=height
        )
        db.add(photo_record)

    db.flush()

    # Run Image Quality Engine
    quality_result = image_quality_engine.evaluate_quality(
        image_path=private_path,
        image_id=photo_record.id,
        angle=angle
    )

    photo_record.quality_status = quality_result["quality_status"]
    db.commit()
    db.refresh(photo_record)

    # Build response with quality details
    res = PhotoResponse(
        id=photo_record.id,
        assessment_id=photo_record.assessment_id,
        angle=photo_record.angle,
        width=photo_record.width,
        height=photo_record.height,
        quality_status=photo_record.quality_status,
        uploaded_at=photo_record.uploaded_at,
        quality_details=quality_result
    )
    return res

@router.get("/assessments/{assessment_id}/photos", response_model=List[PhotoResponse])
def get_assessment_photos(
    assessment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists metadata for all uploaded photos in the assessment (no public binary URLs exposed)."""
    assessment = db.query(Assessment).filter(
        Assessment.id == assessment_id,
        Assessment.user_id == current_user.id
    ).first()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found.")

    photos = db.query(Photo).filter(Photo.assessment_id == assessment_id).all()
    results = []
    for p in photos:
        q_result = image_quality_engine.evaluate_quality(p.private_file_path, p.id, p.angle)
        results.append(PhotoResponse(
            id=p.id,
            assessment_id=p.assessment_id,
            angle=p.angle,
            width=p.width,
            height=p.height,
            quality_status=p.quality_status,
            uploaded_at=p.uploaded_at,
            quality_details=q_result
        ))
    return results

@router.delete("/photos/{photo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Securely deletes a photo and its private stored file on disk."""
    photo = db.query(Photo).join(Assessment).filter(
        Photo.id == photo_id,
        Assessment.user_id == current_user.id
    ).first()
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found.")

    # Remove file from disk
    file_on_disk = Path(photo.private_file_path)
    if file_on_disk.exists():
        try:
            file_on_disk.unlink()
        except Exception:
            pass

    db.delete(photo)
    db.commit()
    return None

