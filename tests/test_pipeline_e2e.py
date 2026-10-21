"""
DataPulse AI - End-to-End Pipeline Integration Test
"""
import pytest
from app.ingestion.pipeline import SalesDataPipeline
from app.warehouse.models import FactSales, RawSalesBatch, PipelineRun


def test_full_pipeline_e2e_execution(db_session):
    """Executes the complete 9-stage pipeline from simulation to Gold warehouse."""
    with SalesDataPipeline(db=db_session) as pipeline:
        result = pipeline.run_pipeline(
            source_type="simulated_api",
            num_simulated_records=100
        )

    summary = result["run_summary"]
    quality = result["quality_report"]
    gold = result["gold_warehouse_stats"]

    assert summary["status"] == "SUCCESS"
    assert summary["records_ingested"] == 100
    assert summary["records_processed"] > 80
    assert summary["records_quarantined"] >= 0
    assert quality["summary"]["health_verdict"] in ["EXCELLENT", "HEALTHY", "ACCEPTABLE_WITH_QUARANTINE"]
    assert gold["fact_sales_loaded"] == summary["records_processed"]

    # Verify database persistence
    assert db_session.query(RawSalesBatch).filter_by(batch_id=summary["batch_id"]).count() == 1
    assert db_session.query(PipelineRun).filter_by(run_id=summary["run_id"]).count() == 1
