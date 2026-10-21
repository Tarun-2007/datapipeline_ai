"""
DataPulse AI - Test Configuration and Fixtures
Provides isolated in-memory test database, sample datasets, and API test client.
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.warehouse.models import *  # noqa: F403
from app.api.app import app
from app.ingestion.generator import SalesDataGenerator


@pytest.fixture(scope="session")
def test_engine():
    """In-memory SQLite engine isolated from development/production with StaticPool."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provides an isolated database session per test with clean schema."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def sample_raw_df():
    """Generates a reproducible 100-record sales dataframe."""
    gen = SalesDataGenerator(seed=123)
    return gen.generate_records(num_records=100, dirty_rate=0.10)


@pytest.fixture(scope="module")
def api_client(test_engine):
    """FastAPI TestClient with overridden database dependency."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
