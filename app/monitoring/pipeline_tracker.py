"""
DataPulse AI - Pipeline Execution Tracker and Reliability Monitoring
Provides execution lifecycle tracing, run duration tracking, status reporting,
and exponential backoff retry decorators for resilient data engineering.
"""
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Optional, Dict, Any, Callable
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.warehouse.models import PipelineRun


def retry_with_backoff(retries: int = 3, backoff_factor: float = 1.5, exceptions: tuple = (Exception,)):
    """
    Decorator for retrying transient operations with exponential backoff.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            delay = 1.0
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= retries:
                        logger.error(f"Function {func.__name__} failed after {retries} attempts: {e}")
                        raise
                    logger.warning(f"Function {func.__name__} attempt {attempt} failed ({e}). Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                    delay *= backoff_factor
        return wrapper
    return decorator


class PipelineTracker:
    """Manages the lifecycle of a pipeline execution run."""

    def __init__(self, db: Session, batch_id: Optional[str] = None, source: str = "batch_pipeline"):
        self.db = db
        self.run_id = f"RUN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"
        self.batch_id = batch_id or f"BATCH-{str(uuid.uuid4())[:8]}"
        self.source = source
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.duration_seconds: Optional[float] = None
        self.records_ingested: int = 0
        self.records_processed: int = 0
        self.records_quarantined: int = 0
        self.status: str = "RUNNING"
        self.error_details: Optional[str] = None

        self._record_start()

    def _record_start(self) -> None:
        """Persists the initial running state into the pipeline_runs table."""
        try:
            run = PipelineRun(
                run_id=self.run_id,
                batch_id=self.batch_id,
                source=self.source,
                start_time=self.start_time,
                status="RUNNING"
            )
            self.db.add(run)
            self.db.commit()
            logger.info(f"Started pipeline run {self.run_id} for batch {self.batch_id} (source: {self.source}).")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record pipeline start for {self.run_id}: {e}")

    def complete_success(
        self,
        records_ingested: int,
        records_processed: int,
        records_quarantined: int
    ) -> Dict[str, Any]:
        """Marks the pipeline run as SUCCESS and updates operational metrics."""
        self.end_time = datetime.utcnow()
        self.duration_seconds = round((self.end_time - self.start_time).total_seconds(), 2)
        self.records_ingested = records_ingested
        self.records_processed = records_processed
        self.records_quarantined = records_quarantined
        self.status = "SUCCESS"

        try:
            run = self.db.query(PipelineRun).filter_by(run_id=self.run_id).first()
            if run:
                run.end_time = self.end_time
                run.duration_seconds = self.duration_seconds
                run.records_ingested = self.records_ingested
                run.records_processed = self.records_processed
                run.records_quarantined = self.records_quarantined
                run.status = "SUCCESS"
                self.db.commit()
            logger.info(f"Pipeline run {self.run_id} finished SUCCESS in {self.duration_seconds}s.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record pipeline success: {e}")

        return self.to_dict()

    def fail(self, error: Exception) -> Dict[str, Any]:
        """Marks the pipeline run as FAILED and captures traceback details."""
        self.end_time = datetime.utcnow()
        self.duration_seconds = round((self.end_time - self.start_time).total_seconds(), 2)
        self.status = "FAILED"
        self.error_details = str(error)

        try:
            run = self.db.query(PipelineRun).filter_by(run_id=self.run_id).first()
            if run:
                run.end_time = self.end_time
                run.duration_seconds = self.duration_seconds
                run.status = "FAILED"
                run.error_details = self.error_details
                self.db.commit()
            logger.error(f"Pipeline run {self.run_id} FAILED: {error}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to record pipeline failure: {e}")

        return self.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        """Returns run summary dictionary."""
        return {
            "run_id": self.run_id,
            "batch_id": self.batch_id,
            "source": self.source,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "records_ingested": self.records_ingested,
            "records_processed": self.records_processed,
            "records_quarantined": self.records_quarantined,
            "status": self.status,
            "error_details": self.error_details
        }
