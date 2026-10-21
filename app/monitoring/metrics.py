"""
DataPulse AI - Operational Metrics & Platform Health Auditing
Provides system health monitoring, SLA tracking, and pipeline execution logs.
"""
import shutil
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.config import settings
from app.core.database import check_connection
from app.warehouse.models import PipelineRun


class PlatformMonitor:
    """Monitors operational health, infrastructure status, and pipeline execution performance."""

    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """Audits database connectivity, disk space, and core runtime status."""
        db_healthy = check_connection()

        # Check local disk capacity
        total, used, free = shutil.disk_usage(str(settings.DATA_DIR))
        free_gb = round(free / (2**30), 2)
        total_gb = round(total / (2**30), 2)

        return {
            "status": "HEALTHY" if db_healthy and free_gb > 1.0 else "DEGRADED",
            "database_connected": db_healthy,
            "disk_free_gb": free_gb,
            "disk_total_gb": total_gb,
            "storage_path": str(settings.DATA_DIR),
            "environment": settings.ENVIRONMENT
        }

    @staticmethod
    def get_pipeline_runs_history(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent pipeline runs ordered chronologically."""
        runs = (
            db.query(PipelineRun)
            .order_by(desc(PipelineRun.start_time))
            .limit(limit)
            .all()
        )

        history = []
        for r in runs:
            history.append({
                "run_id": r.run_id,
                "batch_id": r.batch_id,
                "source": r.source,
                "start_time": r.start_time.strftime("%Y-%m-%d %H:%M:%S") if r.start_time else None,
                "end_time": r.end_time.strftime("%Y-%m-%d %H:%M:%S") if r.end_time else None,
                "duration_seconds": r.duration_seconds,
                "records_ingested": r.records_ingested,
                "records_processed": r.records_processed,
                "records_quarantined": r.records_quarantined,
                "status": r.status,
                "error_details": r.error_details
            })
        return history

    @staticmethod
    def get_pipeline_sla_summary(db: Session) -> Dict[str, Any]:
        """Calculates pipeline uptime and SLA execution metrics."""
        total_runs = db.query(func.count(PipelineRun.run_id)).scalar() or 0
        success_runs = db.query(func.count(PipelineRun.run_id)).filter(PipelineRun.status == "SUCCESS").scalar() or 0
        failed_runs = db.query(func.count(PipelineRun.run_id)).filter(PipelineRun.status == "FAILED").scalar() or 0
        avg_duration = db.query(func.avg(PipelineRun.duration_seconds)).filter(PipelineRun.status == "SUCCESS").scalar() or 0.0

        success_rate = round((success_runs / total_runs) * 100, 2) if total_runs > 0 else 100.0

        return {
            "total_runs": total_runs,
            "successful_runs": success_runs,
            "failed_runs": failed_runs,
            "success_rate_pct": success_rate,
            "avg_duration_seconds": round(float(avg_duration), 2)
        }
