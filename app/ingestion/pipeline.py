"""
DataPulse AI - Master Pipeline Orchestrator
Executes the unified end-to-end data pipeline lifecycle:
Bronze (Ingest & Archive) -> Validation & Quarantine -> Silver (Clean & Staging) -> Gold (Warehouse Loading) -> Quality Audit.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.logging import logger
from app.ingestion.csv_ingestion import CSVIngestionSource
from app.ingestion.api_ingestion import RESTAPIIngestionSource
from app.transformations.validator import DataValidator
from app.transformations.cleaner import DataCleaner
from app.transformations.quality import DataQualityReporter
from app.warehouse.loader import WarehouseLoader
from app.monitoring.pipeline_tracker import PipelineTracker


class SalesDataPipeline:
    """End-to-end data engineering pipeline coordinator."""

    def __init__(self, db: Optional[Session] = None):
        self._external_db = db is not None
        self.db = db or SessionLocal()
        init_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._external_db and self.db:
            self.db.close()

    def run_pipeline(
        self,
        source_type: str = "csv",
        file_path: Optional[str] = None,
        api_url: Optional[str] = None,
        batch_id: Optional[str] = None,
        num_simulated_records: int = 1000
    ) -> Dict[str, Any]:
        """
        Executes the entire 9-stage pipeline sequentially with atomic tracking.
        
        Args:
            source_type: 'csv', 'api', or 'simulated_api'
            file_path: Absolute or relative path to CSV file if source_type == 'csv'
            api_url: HTTP endpoint URL if source_type == 'api'
            batch_id: Optional explicit batch identifier
            num_simulated_records: Count of records if simulating API stream
            
        Returns:
            Dict containing pipeline run statistics and quality report.
        """
        tracker = PipelineTracker(self.db, batch_id=batch_id, source=source_type)
        actual_batch_id = tracker.batch_id

        try:
            logger.info(f"=== Starting Pipeline Run {tracker.run_id} [Batch: {actual_batch_id}] ===")

            # -------------------------------------------------------------
            # Stage 1: Bronze Ingestion & Raw Archival
            # -------------------------------------------------------------
            if source_type == "csv":
                csv_src = CSVIngestionSource()
                if not file_path:
                    # Default sample path
                    file_path = str(settings.DATA_DIR / "sample_sales_5000.csv")
                b_id, raw_df, meta = csv_src.ingest_file(Path(file_path), batch_id=actual_batch_id)
                source_uri = file_path

            elif source_type == "api":
                api_src = RESTAPIIngestionSource()
                b_id, raw_df, meta = api_src.ingest_from_endpoint(api_url, batch_id=actual_batch_id)
                source_uri = api_url

            elif source_type == "simulated_api":
                api_src = RESTAPIIngestionSource()
                b_id, raw_df, meta = api_src.ingest_from_mock_generator(
                    num_records=num_simulated_records, batch_id=actual_batch_id
                )
                source_uri = meta.get("source_uri")

            else:
                raise ValueError(f"Unsupported source_type: {source_type}. Choose 'csv', 'api', or 'simulated_api'.")

            total_received = len(raw_df)
            logger.info(f"Stage 1 Complete: Ingested {total_received} raw records.")

            # -------------------------------------------------------------
            # Stage 2: Schema Validation & Quarantine Segregation
            # -------------------------------------------------------------
            validator = DataValidator(batch_id=actual_batch_id)
            val_result = validator.validate_and_quarantine(raw_df)
            logger.info(
                f"Stage 2 Complete: {val_result.accepted_count} valid, "
                f"{val_result.rejected_count} quarantined ({val_result.rejection_rate*100:.1f}%)."
            )

            # -------------------------------------------------------------
            # Stage 3: Data Cleaning & Normalization
            # -------------------------------------------------------------
            cleaner = DataCleaner(batch_id=actual_batch_id)
            clean_df = cleaner.clean_and_transform(val_result.valid_df)
            logger.info(f"Stage 3 Complete: Cleaned {len(clean_df)} records, computed net_sales.")

            # -------------------------------------------------------------
            # Stage 4: Silver Layer Loading (Staging + Quarantine)
            # -------------------------------------------------------------
            loader = WarehouseLoader(self.db)
            loader.load_staging_and_quarantine(
                batch_id=actual_batch_id,
                clean_df=clean_df,
                quarantine_records=val_result.quarantine_records,
                source=source_type,
                source_uri=source_uri
            )
            logger.info("Stage 4 Complete: Silver staging and quarantine tables loaded idempotently.")

            # -------------------------------------------------------------
            # Stage 5: Data Quality Scorecard Compilation
            # -------------------------------------------------------------
            reporter = DataQualityReporter(batch_id=actual_batch_id)
            quality_report = reporter.build_quality_report(val_result, clean_df)
            logger.info(f"Stage 5 Complete: Quality Verdict = {quality_report['summary']['health_verdict']}.")

            # -------------------------------------------------------------
            # Stage 6: Gold Layer Dimensional Warehouse Promotion
            # -------------------------------------------------------------
            gold_stats = loader.load_warehouse_gold(batch_id=actual_batch_id)
            logger.info(f"Stage 6 Complete: Gold warehouse loaded ({gold_stats['fact_sales_loaded']} facts).")

            # -------------------------------------------------------------
            # Stage 7: Pipeline Run Completion & Metric Finalization
            # -------------------------------------------------------------
            run_summary = tracker.complete_success(
                records_ingested=total_received,
                records_processed=len(clean_df),
                records_quarantined=val_result.rejected_count
            )

            return {
                "run_summary": run_summary,
                "quality_report": quality_report,
                "gold_warehouse_stats": gold_stats
            }

        except Exception as e:
            tracker.fail(e)
            logger.exception(f"Pipeline execution error for batch {actual_batch_id}: {e}")
            raise
