from datetime import datetime
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# ----------------- Auth Schemas -----------------
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    password: str = Field(..., min_length=8)
    consent_processing: bool = True
    consent_research: Optional[bool] = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr
    created_at: datetime

# ----------------- Consent Schemas -----------------
class ConsentCreate(BaseModel):
    consent_type: str
    consent_version: str = "1.0.0"
    accepted: bool

# ----------------- Questionnaire Schemas -----------------
class AnswerItem(BaseModel):
    question_key: str
    answer_value: Any

class QuestionnaireSubmit(BaseModel):
    answers: List[AnswerItem]
    consent_confirmed: bool = True

class QuestionnaireValidationResult(BaseModel):
    is_valid: bool
    missing_fields: List[str] = []
    answers: Dict[str, Any] = {}

# ----------------- Photo Schemas -----------------
class PhotoQualityDetails(BaseModel):
    blur_score: float
    brightness_score: float
    contrast_score: float
    resolution: Dict[str, int]
    is_blurry: bool
    is_dark: bool
    is_overexposed: bool
    is_low_contrast: bool
    warnings: List[str]

class PhotoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    angle: str
    width: int
    height: int
    quality_status: str  # acceptable, needs_improvement, rejected
    uploaded_at: datetime
    quality_details: Optional[PhotoQualityDetails] = None

# ----------------- Feature Extraction & Analysis Schemas -----------------
class AngleFeatureData(BaseModel):
    angle: str
    scalp_visible_ratio: Optional[float] = None
    hair_pixel_ratio: Optional[float] = None
    mean_brightness: float
    contrast: float
    hair_color_distribution: Dict[str, float]
    region_of_interest: Dict[str, int]
    lighting_uniformity: float
    notes: List[str] = []

class ImageAnalysisResponse(BaseModel):
    id: str
    photo_id: str
    preprocessing_version: str
    model_version: str
    analysis_status: str
    feature_data: Dict[str, Any]
    confidence_data: Dict[str, Any]

# ----------------- Assessment Schemas -----------------
class AssessmentCreate(BaseModel):
    pass

class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    assessment_status: str
    questionnaire_version: str
    engine_version: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    photo_count: int = 0
    photos: List[PhotoResponse] = []

# ----------------- Report Schemas -----------------
class ReportSection(BaseModel):
    title: str
    content: Any

class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    report_version: str
    generated_at: datetime
    report_data: Dict[str, Any]
