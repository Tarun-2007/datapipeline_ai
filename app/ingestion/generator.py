"""
DataPulse AI - Synthetic Retail Sales Generator
Generates realistic retail sales transactions with configurable data quality issues
to test ingestion, schema validation, quarantine rules, and ML pipelines.
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np


# Catalog of products across realistic retail categories
PRODUCT_CATALOG = [
    {"product_id": "PRD-101", "product_name": "Ultra HD 4K Monitor", "category": "Electronics", "base_price": 349.99},
    {"product_id": "PRD-102", "product_name": "Wireless Noise-Canceling Headphones", "category": "Electronics", "base_price": 199.50},
    {"product_id": "PRD-103", "product_name": "Mechanical Gaming Keyboard", "category": "Electronics", "base_price": 89.99},
    {"product_id": "PRD-104", "product_name": "Smart Fitness Watch", "category": "Electronics", "base_price": 149.00},
    {"product_id": "PRD-105", "product_name": "Ergonomic Office Chair", "category": "Home & Office", "base_price": 279.00},
    {"product_id": "PRD-106", "product_name": "Standing Desk Converter", "category": "Home & Office", "base_price": 185.00},
    {"product_id": "PRD-107", "product_name": "Ceramic Pour-Over Coffee Maker", "category": "Home & Kitchen", "base_price": 38.50},
    {"product_id": "PRD-108", "product_name": "Stainless Steel Cookware Set", "category": "Home & Kitchen", "base_price": 219.00},
    {"product_id": "PRD-109", "product_name": "Organic Cotton Hoodie", "category": "Apparel", "base_price": 54.00},
    {"product_id": "PRD-110", "product_name": "Water-Resistant Running Shoes", "category": "Apparel", "base_price": 115.00},
    {"product_id": "PRD-111", "product_name": "Breathable Yoga Pants", "category": "Apparel", "base_price": 48.00},
    {"product_id": "PRD-112", "product_name": "Insulated Hydro Water Bottle", "category": "Sports & Outdoors", "base_price": 28.00},
    {"product_id": "PRD-113", "product_name": "Camping 2-Person Dome Tent", "category": "Sports & Outdoors", "base_price": 169.00},
    {"product_id": "PRD-114", "product_name": "Adjustable Dumbbell Set", "category": "Sports & Outdoors", "base_price": 299.00},
    {"product_id": "PRD-115", "product_name": "Data Science from Scratch Book", "category": "Books", "base_price": 42.00},
    {"product_id": "PRD-116", "product_name": "Designing Data-Intensive Apps", "category": "Books", "base_price": 49.99},
]

REGIONS = ["North", "South", "East", "West", "Central"]
INCONSISTENT_REGIONS = ["north", "SOUTH", "  East ", "west", "CENTRAL"]
INCONSISTENT_CATEGORIES = ["electronics", "ELECTRONICS", "home & kitchen", "APPAREL", "sports & outdoors"]


class SalesDataGenerator:
    """
    Synthesizes retail transaction records with realistic volume patterns,
    seasonal trends, and deliberate edge-case dirty records to stress-test data pipelines.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def generate_records(
        self,
        num_records: int = 5000,
        start_date: str = "2024-01-01",
        end_date: str = "2024-06-30",
        dirty_rate: float = 0.05
    ) -> pd.DataFrame:
        """
        Generates realistic sales transactions.
        
        Args:
            num_records: Total count of records to generate (>= 5000)
            start_date: Start date string (YYYY-MM-DD)
            end_date: End date string (YYYY-MM-DD)
            dirty_rate: Ratio of rows injected with intentional quality flaws (0.0 to 1.0)
            
        Returns:
            pd.DataFrame: Raw synthetic sales dataframe
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end_dt - start_dt).days + 1

        customer_ids = [f"CUST-{1000 + i}" for i in range(500)]
        records: List[Dict[str, Any]] = []

        for i in range(num_records):
            # Choose a date with realistic day-of-week weighting (higher sales on Fri/Sat/Sun)
            day_offset = random.randint(0, total_days - 1)
            txn_date = start_dt + timedelta(days=day_offset)

            # Product selection
            prod = random.choice(PRODUCT_CATALOG)
            customer = random.choice(customer_ids)
            region = random.choice(REGIONS)

            # Realistic quantity distribution (mostly 1-3, occasionally bulk 4-10)
            quantity = np.random.choice([1, 2, 3, 4, 5, 8, 10], p=[0.55, 0.22, 0.12, 0.05, 0.03, 0.02, 0.01])
            
            # Unit price with small variance around catalog base
            price_variation = round(random.uniform(-0.05, 0.05) * prod["base_price"], 2)
            unit_price = round(prod["base_price"] + price_variation, 2)

            # Discounts: 0% standard, occasionally 5%, 10%, 15%, 20%
            discount = float(np.random.choice([0.0, 0.05, 0.10, 0.15, 0.20], p=[0.60, 0.15, 0.12, 0.08, 0.05]))

            rec = {
                "transaction_id": f"TXN-{100000 + i}",
                "transaction_date": txn_date.strftime("%Y-%m-%d"),
                "product_id": prod["product_id"],
                "product_name": prod["product_name"],
                "category": prod["category"],
                "quantity": int(quantity),
                "unit_price": float(unit_price),
                "discount": float(discount),
                "region": region,
                "customer_id": customer
            }
            records.append(rec)

        # Inject controlled dirty/malformed records if dirty_rate > 0
        if dirty_rate > 0:
            dirty_count = int(num_records * dirty_rate)
            dirty_indices = random.sample(range(num_records), dirty_count)

            for idx in dirty_indices:
                flaw_type = random.choice([
                    "duplicate_id",
                    "missing_customer",
                    "invalid_date",
                    "negative_quantity",
                    "negative_price",
                    "extreme_discount",
                    "inconsistent_case",
                    "null_product_id"
                ])

                if flaw_type == "duplicate_id" and idx > 5:
                    # Duplicate an earlier transaction_id
                    records[idx]["transaction_id"] = records[idx - 5]["transaction_id"]

                elif flaw_type == "missing_customer":
                    records[idx]["customer_id"] = None

                elif flaw_type == "invalid_date":
                    records[idx]["transaction_date"] = "2024-99-99"

                elif flaw_type == "negative_quantity":
                    records[idx]["quantity"] = -random.randint(1, 5)

                elif flaw_type == "negative_price":
                    records[idx]["unit_price"] = -50.0

                elif flaw_type == "extreme_discount":
                    records[idx]["discount"] = 1.75  # 175% discount is illegal

                elif flaw_type == "inconsistent_case":
                    records[idx]["category"] = random.choice(INCONSISTENT_CATEGORIES)
                    records[idx]["region"] = random.choice(INCONSISTENT_REGIONS)

                elif flaw_type == "null_product_id":
                    records[idx]["product_id"] = None

        df = pd.DataFrame(records)
        return df


def generate_and_save_dataset(
    output_path: str,
    num_records: int = 5000,
    dirty_rate: float = 0.05,
    seed: int = 42
) -> str:
    """Convenience helper to generate and save synthetic dataset directly to CSV."""
    generator = SalesDataGenerator(seed=seed)
    df = generator.generate_records(num_records=num_records, dirty_rate=dirty_rate)
    df.to_csv(output_path, index=False)
    return output_path
