import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

logger = logging.getLogger("hair_ai.database")

Base = declarative_base()

def get_engine():
    db_uri = settings.SQLALCHEMY_DATABASE_URI
    try:
        # Test connecting if MySQL
        engine = create_engine(
            db_uri,
            pool_pre_ping=True,
            echo=False,
            pool_recycle=3600
        )
        with engine.connect() as conn:
            pass
        logger.info(f"Connected to database at {db_uri.split('@')[-1]}")
        return engine
    except Exception as e:
        logger.warning(
            f"Could not connect to configured DB ({db_uri.split('@')[-1] if '@' in db_uri else db_uri}): {e}. "
            f"Falling back to local SQLite database for portable development."
        )
        sqlite_path = settings.STORAGE_DIR / "hair_ai_portable.db"
        sqlite_uri = f"sqlite:///{sqlite_path}"
        engine = create_engine(
            sqlite_uri,
            connect_args={"check_same_thread": False},
            echo=False
        )
        return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

