"""
DataPulse AI - Simulated REST API Ingestion Client
Handles paginated API ingestion, incremental page traversing, exponential backoff retries,
and raw Bronze JSON archiving.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional
import pandas as pd
import requests

from app.core.config import settings
from app.core.logging import logger
from app.monitoring.pipeline_tracker import retry_with_backoff


class RESTAPIIngestionSource:
    """Ingests sales transactions from paginated REST APIs into Bronze raw storage."""

    def __init__(self, raw_storage_dir: Path = None):
        self.raw_storage_dir = raw_storage_dir or settings.RAW_DATA_DIR
        self.raw_storage_dir.mkdir(parents=True, exist_ok=True)

    @retry_with_backoff(retries=3, backoff_factor=1.5, exceptions=(requests.RequestException,))
    def _fetch_page(self, endpoint_url: str, page: int, page_size: int = 100) -> Dict[str, Any]:
        """Fetches a single page with timeout and automatic retry on network errors."""
        response = requests.get(
            endpoint_url,
            params={"page": page, "page_size": page_size},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def ingest_from_endpoint(
        self,
        endpoint_url: str,
        max_pages: Optional[int] = None,
        page_size: int = 100,
        batch_id: Optional[str] = None
    ) -> Tuple[str, pd.DataFrame, Dict[str, Any]]:
        """
        Traverses paginated REST API responses to collect records into a unified batch.
        """
        batch_id = batch_id or f"BATCH-API-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"
        all_records: List[Dict[str, Any]] = []

        current_page = 1
        total_pages = 1

        while True:
            logger.info(f"Fetching API page {current_page} from {endpoint_url}...")
            payload = self._fetch_page(endpoint_url, page=current_page, page_size=page_size)

            items = payload.get("data", [])
            all_records.extend(items)
            total_pages = payload.get("total_pages", 1)

            if current_page >= total_pages or (max_pages and current_page >= max_pages):
                break
            current_page += 1

        df = pd.DataFrame(all_records)

        # Archive raw Bronze JSON payload
        bronze_filename = f"{batch_id}_api_response.json"
        bronze_file = self.raw_storage_dir / bronze_filename
        with open(bronze_file, "w", encoding="utf-8") as f:
            json.dump({"batch_id": batch_id, "endpoint": endpoint_url, "records": all_records}, f, indent=2)

        metadata = {
            "batch_id": batch_id,
            "source": "rest_api",
            "source_uri": endpoint_url,
            "bronze_path": str(bronze_file),
            "pages_fetched": current_page,
            "row_count": len(df),
            "ingested_at": datetime.utcnow().isoformat()
        }

        logger.info(f"Completed REST API ingestion batch {batch_id}: {len(df)} records across {current_page} pages.")
        return batch_id, df, metadata

    def ingest_from_mock_generator(
        self,
        num_records: int = 500,
        batch_id: Optional[str] = None
    ) -> Tuple[str, pd.DataFrame, Dict[str, Any]]:
        """
        Simulates in-memory paginated REST responses without requiring active network port.
        Ideal for local unit testing and quick demonstrations.
        """
        from app.ingestion.generator import SalesDataGenerator
        batch_id = batch_id or f"BATCH-API-SIM-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:6]}"

        gen = SalesDataGenerator(seed=int(datetime.utcnow().timestamp()) % 100000)
        df = gen.generate_records(num_records=num_records, dirty_rate=0.04)

        # Archive raw Bronze file
        bronze_file = self.raw_storage_dir / f"{batch_id}_simulated_api.json"
        with open(bronze_file, "w", encoding="utf-8") as f:
            json.dump({"batch_id": batch_id, "source": "simulated_api", "records": df.to_dict(orient="records")}, f, indent=2)

        metadata = {
            "batch_id": batch_id,
            "source": "simulated_rest_api",
            "source_uri": "mock://internal.sales.service/v1/transactions",
            "bronze_path": str(bronze_file),
            "row_count": len(df),
            "ingested_at": datetime.utcnow().isoformat()
        }
        return batch_id, df, metadata
