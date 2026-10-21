"""
DataPulse AI - CSV File Ingestion Engine
Handles raw CSV ingestion, Bronze raw file archiving, checksum calculation, and idempotency tracking.
"""
import hashlib
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any
import pandas as pd

from app.core.config import settings
from app.core.logging import logger


class CSVIngestionSource:
    """Ingests retail sales CSV data into Bronze raw storage with cryptographic checksum validation."""

    def __init__(self, raw_storage_dir: Path = None):
        self.raw_storage_dir = raw_storage_dir or settings.RAW_DATA_DIR
        self.raw_storage_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_checksum(file_path: Path) -> str:
        """Computes SHA256 checksum for byte-level idempotency checks."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def ingest_file(self, source_path: Path, batch_id: str = None) -> Tuple[str, pd.DataFrame, Dict[str, Any]]:
        """
        Ingests a CSV file into the Bronze layer.
        
        Args:
            source_path: Path to the incoming CSV file
            batch_id: Optional explicit batch ID; generated if None
            
        Returns:
            Tuple of (batch_id, raw_dataframe, metadata_dict)
        """
        source_path = Path(source_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Source CSV file not found: {source_path}")

        batch_id = batch_id or f"BATCH-CSV-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"
        checksum = self.calculate_checksum(source_path)

        # Preserve Bronze raw file copy
        bronze_filename = f"{batch_id}_{source_path.name}"
        bronze_destination = self.raw_storage_dir / bronze_filename
        shutil.copy2(source_path, bronze_destination)

        # Ingest dataframe preserving raw contents
        raw_df = pd.read_csv(source_path)

        metadata = {
            "batch_id": batch_id,
            "source": "csv",
            "source_file": source_path.name,
            "bronze_path": str(bronze_destination),
            "checksum": checksum,
            "row_count": len(raw_df),
            "ingested_at": datetime.utcnow().isoformat()
        }

        logger.info(f"Ingested CSV batch {batch_id}: {len(raw_df)} records, checksum {checksum[:8]}...")
        return batch_id, raw_df, metadata
