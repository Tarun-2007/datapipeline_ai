"""
DataPulse AI - Logging Module
Provides standardized, structured logging across all pipeline, API, and ML modules.
"""
import sys
import logging
from pathlib import Path
from app.core.config import settings


def setup_logger(name: str = "datapulse") -> logging.Logger:
    """Configures and returns a logger instance with console and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Avoid duplicate handlers if already initialized
    if logger.handlers:
        return logger

    # Format
    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler
    log_file = settings.LOGS_DIR / "datapulse.log"
    try:
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # Fallback to console only if file cannot be created
        pass

    logger.propagate = False
    return logger


logger = setup_logger("datapulse")
