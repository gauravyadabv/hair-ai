import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Float, JSON
)
from sqlalchemy.orm import relationship
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    assessments = relationship("Assessment", back_populates="user", cascade="all, delete-orphan")
    consent_records = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(100), nullable=False)  # 'assessment_processing', 'optional_research'
    consent_version = Column(String(50), nullable=False)
    accepted = Column(Boolean, default=True, nullable=False)
    accepted_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="consent_records")


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_status = Column(String(50), default="pending", nullable=False) # pending, questionnaire_completed, photos_uploaded, analyzed, completed
    questionnaire_version = Column(String(50), nullable=False, default="1.0.0")
    engine_version = Column(String(50), nullable=False, default="1.0.0")
    created_at = Column(DateTime, default=utc_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="assessments")
    answers = relationship("QuestionnaireAnswer", back_populates="assessment", cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="assessment", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="assessment", cascade="all, delete-orphan")


class QuestionnaireAnswer(Base):
    __tablename__ = "questionnaire_answers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question_key = Column(String(100), nullable=False, index=True)
    answer_value = Column(Text, nullable=False)  # JSON-encoded string or text value
    created_at = Column(DateTime, default=utc_now, nullable=False)

    assessment = relationship("Assessment", back_populates="answers")


class Photo(Base):
    __tablename__ = "photos"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    angle = Column(String(50), nullable=False)  # 'front_hairline', 'top_scalp', 'crown', 'left_temple', 'right_temple'
    private_file_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA256
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    quality_status = Column(String(50), default="pending", nullable=False) # pending, acceptable, needs_improvement, rejected
    uploaded_at = Column(DateTime, default=utc_now, nullable=False)

    assessment = relationship("Assessment", back_populates="photos")
    analyses = relationship("ImageAnalysis", back_populates="photo", cascade="all, delete-orphan")


class ImageAnalysis(Base):
    __tablename__ = "image_analysis"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    photo_id = Column(String(36), ForeignKey("photos.id", ondelete="CASCADE"), nullable=False, index=True)
    preprocessing_version = Column(String(50), nullable=False, default="1.0.0")
    model_version = Column(String(50), nullable=False, default="unet-v1.0-baseline")
    analysis_status = Column(String(50), default="completed", nullable=False)  # pending, completed, failed
    feature_data_json = Column(JSON, nullable=True)
    confidence_data_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    photo = relationship("Photo", back_populates="analyses")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    assessment_id = Column(String(36), ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    report_version = Column(String(50), nullable=False, default="1.0.0")
    report_data_json = Column(JSON, nullable=False)
    pdf_file_path = Column(String(500), nullable=True)
    generated_at = Column(DateTime, default=utc_now, nullable=False)

    assessment = relationship("Assessment", back_populates="reports")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), unique=True, nullable=False)
    model_file_path = Column(String(500), nullable=True)
    training_dataset_version = Column(String(100), nullable=True)
    evaluation_status = Column(String(50), default="experimental", nullable=False) # experimental, validated, deprecated
    deployed_at = Column(DateTime, default=utc_now, nullable=False)

