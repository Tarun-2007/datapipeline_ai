import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from app.core.config import settings
from app.ingestion.generator import generate_and_save_dataset


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic retail sales dataset.")
    parser.add_argument("--records", type=int, default=5000, help="Number of records to generate (default: 5000)")
    parser.add_argument("--dirty-rate", type=float, default=0.04, help="Ratio of deliberate quality errors (default: 0.04)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--output", type=str, default=str(settings.DATA_DIR / "sample_sales_5000.csv"), help="Output CSV path")

    args = parser.parse_args()
    print(f"Generating {args.records} synthetic sales records (dirty rate: {args.dirty_rate*100:.1f}%, seed: {args.seed})...")
    out = generate_and_save_dataset(args.output, num_records=args.records, dirty_rate=args.dirty_rate, seed=args.seed)
    print(f"Dataset successfully created at: {out}")


if __name__ == "__main__":
    main()
