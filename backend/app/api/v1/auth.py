from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from app.models.models import User, ConsentRecord
from app.schemas.schemas import UserRegister, UserLogin, Token, UserResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    # Check if user already exists
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address is already registered."
        )

    # Hash password with Argon2id
    hashed_pwd = get_password_hash(payload.password)
    new_user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hashed_pwd
    )
    db.add(new_user)
    db.flush()  # get user id

    # Record consent records
    # 1. Processing consent (required for assessment)
    consent_proc = ConsentRecord(
        user_id=new_user.id,
        consent_type="assessment_processing",
        consent_version="1.0.0",
        accepted=payload.consent_processing
    )
    db.add(consent_proc)

    # 2. Optional research consent
    if payload.consent_research:
        consent_res = ConsentRecord(
            user_id=new_user.id,
            consent_type="optional_research",
            consent_version="1.0.0",
            accepted=True
        )
        db.add(consent_res)

    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(subject=new_user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

