from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Hair Health AI Core Engine"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"

    # Database
    # Default is MySQL 8 as requested by PRD, with fallback to SQLite for local portable dev if MySQL is absent
    MYSQL_USER: str = "hair_ai_user"
    MYSQL_PASSWORD: str = "hair_ai_password"
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_DB: str = "hair_ai"
    
    # Optional override: If set, uses DATABASE_URL directly
    DATABASE_URL: str | None = None

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # Try MySQL connection string
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4"

    # Security
    SECRET_KEY: str = "hair-health-ai-secret-key-change-in-production-secure-32b"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Storage Paths (Docker-free local storage)
    STORAGE_DIR: Path = BASE_DIR / "storage"
    PHOTOS_DIR: Path = BASE_DIR / "storage" / "photos"
    REPORTS_DIR: Path = BASE_DIR / "storage" / "reports"
    ML_MODELS_DIR: Path = BASE_DIR / "ml" / "models"

    # Image Upload Constraints (Module B)
    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MIN_IMAGE_DIMENSION: int = 512                # 512x512
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png"]
    ALLOWED_EXTENSIONS: list[str] = [".jpg", ".jpeg", ".png"]

    # Image Quality Thresholds (Module C)
    BLUR_THRESHOLD_LAPLACIAN: float = 100.0       # below is blurry
    BRIGHTNESS_MIN: float = 40.0                 # below is too dark
    BRIGHTNESS_MAX: float = 220.0                # above is overexposed
    CONTRAST_MIN: float = 25.0                   # below is washed out / low contrast

    # Engine Versions
    ENGINE_VERSION: str = "1.0.0"
    QUESTIONNAIRE_VERSION: str = "1.0.0"
    REPORT_VERSION: str = "1.0.0"
    PREPROCESSING_VERSION: str = "1.0.0"
    DEFAULT_MODEL_VERSION: str = "unet-v1.0-baseline"

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
# Ensure directories exist
settings.PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.ML_MODELS_DIR.mkdir(parents=True, exist_ok=True)

