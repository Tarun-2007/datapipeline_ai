import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from app.core.config import settings
from app.ingestion.pipeline import SalesDataPipeline


def main():
    parser = argparse.ArgumentParser(description="Execute DataPulse AI ingestion pipeline.")
    parser.add_argument("--source", type=str, default="csv", choices=["csv", "api", "simulated_api"], help="Ingestion source")
    parser.add_argument("--file", type=str, default=str(settings.DATA_DIR / "sample_sales_5000.csv"), help="CSV input path")
    parser.add_argument("--records", type=int, default=1000, help="Record count for simulated API")
    parser.add_argument("--batch-id", type=str, default=None, help="Explicit batch identifier")

    args = parser.parse_args()
    print(f"Executing pipeline with source: {args.source}...")

    with SalesDataPipeline() as pipeline:
        result = pipeline.run_pipeline(
            source_type=args.source,
            file_path=args.file,
            batch_id=args.batch_id,
            num_simulated_records=args.records
        )

    summary = result["run_summary"]
    quality = result["quality_report"]["summary"]
    gold = result["gold_warehouse_stats"]

    print("=" * 60)
    print("PIPELINE EXECUTION COMPLETE")
    print("=" * 60)
    print(f"Run ID:              {summary['run_id']}")
    print(f"Batch ID:            {summary['batch_id']}")
    print(f"Status:              {summary['status']}")
    print(f"Duration:            {summary['duration_seconds']}s")
    print(f"Records Ingested:    {summary['records_ingested']}")
    print(f"Records Cleaned:     {summary['records_processed']}")
    print(f"Records Quarantined: {summary['records_quarantined']} ({quality['rejection_rate_pct']}%)")
    print(f"Health Verdict:      {quality['health_verdict']}")
    print(f"Gold Facts Loaded:   {gold['fact_sales_loaded']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
