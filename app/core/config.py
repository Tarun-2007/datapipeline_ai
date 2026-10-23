"""
DataPulse AI - Core Configuration Module
Manages environment variables, directory paths, and runtime settings.
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine base project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Platform configuration settings with sensible defaults."""
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "DataPulse AI"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database Configuration
    # Supports PostgreSQL as primary, with SQLite as seamless local fallback
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'datapulse.db'}"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # API Configuration
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    API_BASE_URL: Optional[str] = None

    # Dashboard Configuration
    DASHBOARD_PORT: int = 8501

    # Storage Paths
    DATA_DIR: Path = BASE_DIR / "data"
    RAW_DATA_DIR: Path = BASE_DIR / "data" / "raw"
    PROCESSED_DATA_DIR: Path = BASE_DIR / "data" / "processed"
    QUARANTINE_DATA_DIR: Path = BASE_DIR / "data" / "quarantine"
    MODEL_DIR: Path = BASE_DIR / "app" / "ml" / "saved_models"
    LOGS_DIR: Path = BASE_DIR / "logs"

    # Data Quality Thresholds
    MAX_ALLOWED_REJECTION_RATE: float = 0.20  # 20% max rejected before warning

    def init_directories(self) -> None:
        """Ensure all required runtime data and model directories exist."""
        for path in [
            self.DATA_DIR,
            self.RAW_DATA_DIR,
            self.PROCESSED_DATA_DIR,
            self.QUARANTINE_DATA_DIR,
            self.MODEL_DIR,
            self.LOGS_DIR
        ]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.init_directories()
