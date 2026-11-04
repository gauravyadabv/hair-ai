from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.v1 import auth, assessments, photos, analysis, reports, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all tables are created on startup
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Independent Hair Health Assessment & Intelligence Engine",
    lifespan=lifespan
)

# CORS configuration - allow all origins for easy development and testing
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(assessments.router, prefix=settings.API_V1_STR)
app.include_router(photos.router, prefix=settings.API_V1_STR)
app.include_router(analysis.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Health"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "engine_version": settings.ENGINE_VERSION,
        "status": "operational",
        "pipeline": "Hair Test -> Photo Upload -> Image Processing -> Feature Extraction -> Assessment -> Report"
    }

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}

