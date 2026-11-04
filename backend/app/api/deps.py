from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token, get_password_hash
from app.models.models import User, ConsentRecord

# Make tokenUrl optional so endpoints can be tested without authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def get_or_create_test_user(db: Session) -> User:
    """Provides a guaranteed persistent test user for frictionless testing without login."""
    test_email = "tester@hairhealth.ai"
    user = db.query(User).filter(User.email == test_email).first()
    if not user:
        user = User(
            name="Testing Guest",
            email=test_email,
            password_hash=get_password_hash("test-password-123")
        )
        db.add(user)
        db.flush()
        # Add default consent
        consent = ConsentRecord(
            user_id=user.id,
            consent_type="assessment_processing",
            consent_version="1.0.0",
            accepted=True
        )
        db.add(consent)
        db.commit()
        db.refresh(user)
    return user

def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> User:
    """
    If a valid JWT token is provided, uses that user.
    If no token is provided (Fast Testing Mode), automatically uses the test user.
    """
    if token:
        payload = decode_access_token(token)
        if payload and payload.get("sub"):
            user = db.query(User).filter(User.id == payload.get("sub")).first()
            if user:
                return user

    # Seamless fallback for testing without login
    return get_or_create_test_user(db)
