import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.core.database import init_db
from app.ingestion.generator import generate_and_save_dataset
from app.ingestion.pipeline import SalesDataPipeline
from scripts.train_models import main as train_models_main


def seed():
    print("=" * 65)
    print("DATAPULSE AI - SEEDING COMPLETE PLATFORM DEMONSTRATION DATA")
    print("=" * 65)

    # 1. Initialize schema
    print("\n[Step 1/4] Initializing database schema...")
    init_db()

    # 2. Generate sample CSV dataset
    sample_csv = settings.DATA_DIR / "sample_sales_5000.csv"
    print(f"\n[Step 2/4] Synthesizing 5,000 retail sales records (dirty rate: 4%)...")
    generate_and_save_dataset(str(sample_csv), num_records=5000, dirty_rate=0.04, seed=42)
    print(f"  -> Generated raw sample dataset at: {sample_csv}")

    # 3. Ingest and warehouse through pipeline
    print(f"\n[Step 3/4] Ingesting batch through full data pipeline...")
    with SalesDataPipeline() as pipeline:
        result = pipeline.run_pipeline(source_type="csv", file_path=str(sample_csv))
    
    summary = result["run_summary"]
    quality = result["quality_report"]["summary"]
    gold = result["gold_warehouse_stats"]
    print(f"  -> Pipeline Status:     {summary['status']}")
    print(f"  -> Valid Records Stored: {summary['records_processed']}")
    print(f"  -> Quarantined Records:  {summary['records_quarantined']} ({quality['rejection_rate_pct']}%)")
    print(f"  -> Gold Facts Created:   {gold['fact_sales_loaded']}")

    # 4. Train predictive ML models
    print(f"\n[Step 4/4] Training predictive AI models (Forecasting + Anomaly Detection)...")
    train_models_main()

    print("\n" + "=" * 65)
    print("SUCCESS: DataPulse AI platform is fully seeded and ready for exploration!")
    print("=" * 65)


if __name__ == "__main__":
    seed()
