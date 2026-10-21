"""
DataPulse AI - Database Engine and Session Management
Supports both PostgreSQL (production) and SQLite (zero-config local fallback).
"""
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings
from app.core.logging import logger

Base = declarative_base()


def get_engine(database_url: str = None):
    """Creates a SQLAlchemy engine configured for PostgreSQL or SQLite."""
    url = database_url or settings.DATABASE_URL
    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=False
        )
    else:
        engine = create_engine(
            url,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=False
        )
    return engine


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_connection() -> bool:
    """Verifies database connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def init_db(target_engine=None) -> None:
    """Initializes all database tables registered with Base."""
    eng = target_engine or engine
    logger.info("Initializing database schema...")
    # Import models to register them with Base before create_all
    import app.warehouse.models  # noqa: F401
    Base.metadata.create_all(bind=eng)
    logger.info("Database schema initialized successfully.")
