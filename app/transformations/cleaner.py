"""
DataPulse AI - Data Cleaning and Transformation Engine
Standardizes dimensions, cleans textual attributes, and computes financial metrics (net sales).
"""
from typing import Dict
import pandas as pd
import numpy as np
from app.core.logging import logger

# Canonical mappings for standardizing regional and category data
CATEGORY_MAPPING: Dict[str, str] = {
    "electronics": "Electronics",
    "home & kitchen": "Home & Kitchen",
    "home & office": "Home & Office",
    "apparel": "Apparel",
    "sports & outdoors": "Sports & Outdoors",
    "books": "Books"
}

REGION_MAPPING: Dict[str, str] = {
    "north": "North",
    "south": "South",
    "east": "East",
    "west": "West",
    "central": "Central"
}


class DataCleaner:
    """Transforms validated raw records into high-fidelity staging data."""

    def __init__(self, batch_id: str):
        self.batch_id = batch_id

    def clean_and_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies canonical casing, whitespace trimming, date formatting,
        and derives financial metrics like net_sales.
        """
        if df.empty:
            return df.copy()

        clean_df = df.copy()

        # 1. Clean string identifiers
        clean_df["transaction_id"] = clean_df["transaction_id"].astype(str).str.strip()
        clean_df["product_id"] = clean_df["product_id"].astype(str).str.strip().str.upper()
        clean_df["customer_id"] = clean_df["customer_id"].astype(str).str.strip().str.upper()
        clean_df["product_name"] = clean_df["product_name"].astype(str).str.strip()

        # 2. Standardize Category
        clean_df["category"] = (
            clean_df["category"]
            .astype(str)
            .str.strip()
            .apply(lambda c: CATEGORY_MAPPING.get(c.lower(), c.title()))
        )

        # 3. Standardize Region
        clean_df["region"] = (
            clean_df["region"]
            .astype(str)
            .str.strip()
            .apply(lambda r: REGION_MAPPING.get(r.lower(), r.title()))
        )

        # 4. Standardize Dates
        clean_df["transaction_date"] = pd.to_datetime(clean_df["transaction_date"]).dt.date

        # 5. Type coercions & numeric rounding
        clean_df["quantity"] = clean_df["quantity"].astype(int)
        clean_df["unit_price"] = clean_df["unit_price"].astype(float).round(2)
        clean_df["discount"] = clean_df["discount"].astype(float).round(4)

        # 6. Compute Net Sales
        # net_sales = quantity * unit_price * (1 - discount)
        clean_df["net_sales"] = (
            clean_df["quantity"] * clean_df["unit_price"] * (1.0 - clean_df["discount"])
        ).round(2)

        # 7. Add Batch ID metadata
        clean_df["batch_id"] = self.batch_id

        logger.info(f"Batch {self.batch_id} cleaned & transformed: {len(clean_df)} records.")
        return clean_df
