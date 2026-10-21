"""
DataPulse AI - Unit Tests for Multi-Source Data Ingestion
"""
import pytest
from pathlib import Path
import pandas as pd
from app.ingestion.csv_ingestion import CSVIngestionSource
from app.ingestion.api_ingestion import RESTAPIIngestionSource
from app.ingestion.generator import generate_and_save_dataset


def test_csv_ingestion_and_checksum(tmp_path):
    """Verifies CSV ingestion produces valid checksum and archives Bronze copy."""
    test_csv = tmp_path / "test_sales.csv"
    generate_and_save_dataset(str(test_csv), num_records=25, dirty_rate=0.0)

    bronze_dir = tmp_path / "bronze"
    src = CSVIngestionSource(raw_storage_dir=bronze_dir)
    batch_id, df, meta = src.ingest_file(test_csv)

    assert batch_id.startswith("BATCH-CSV-")
    assert len(df) == 25
    assert len(meta["checksum"]) == 64  # SHA256 length
    assert Path(meta["bronze_path"]).exists()


def test_simulated_api_ingestion(tmp_path):
    """Verifies simulated paginated REST API ingestion generates valid Bronze payloads."""
    bronze_dir = tmp_path / "bronze"
    src = RESTAPIIngestionSource(raw_storage_dir=bronze_dir)
    batch_id, df, meta = src.ingest_from_mock_generator(num_records=50)

    assert batch_id.startswith("BATCH-API-SIM-")
    assert len(df) == 50
    assert Path(meta["bronze_path"]).exists()
    assert meta["source"] == "simulated_rest_api"
