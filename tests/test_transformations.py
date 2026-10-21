"""
DataPulse AI - Unit Tests for Data Transformations & Financial Calculations
"""
import pytest
import pandas as pd
from app.transformations.cleaner import DataCleaner


def test_net_sales_calculation():
    """Verifies net_sales arithmetic formula: quantity * unit_price * (1 - discount)."""
    records = [
        {"transaction_id": "TXN-1", "transaction_date": "2024-01-15", "product_id": "PRD-1", "product_name": "Headphones", "category": "Electronics", "quantity": 2, "unit_price": 100.0, "discount": 0.10, "region": "North", "customer_id": "C-1"},
        {"transaction_id": "TXN-2", "transaction_date": "2024-01-16", "product_id": "PRD-2", "product_name": "Chair", "category": "Home & Office", "quantity": 1, "unit_price": 250.0, "discount": 0.0, "region": "South", "customer_id": "C-2"},
    ]
    df = pd.DataFrame(records)
    cleaner = DataCleaner(batch_id="TEST-CLEAN-01")
    res = cleaner.clean_and_transform(df)

    # 2 * 100 * (1 - 0.10) = 180.0
    assert res.loc[0, "net_sales"] == 180.0
    # 1 * 250 * (1 - 0.0) = 250.0
    assert res.loc[1, "net_sales"] == 250.0


def test_categorical_standardization():
    """Verifies category and region values are canonically capitalized and trimmed."""
    records = [
        {"transaction_id": "TXN-3", "transaction_date": "2024-01-15", "product_id": "prd-3", "product_name": "  Book  ", "category": "books", "quantity": 1, "unit_price": 40.0, "discount": 0.0, "region": "south", "customer_id": "c-3"},
        {"transaction_id": "TXN-4", "transaction_date": "2024-01-15", "product_id": "PRD-4", "product_name": "Tent", "category": "SPORTS & OUTDOORS", "quantity": 1, "unit_price": 150.0, "discount": 0.05, "region": "  west ", "customer_id": "C-4"},
    ]
    df = pd.DataFrame(records)
    cleaner = DataCleaner(batch_id="TEST-CLEAN-02")
    res = cleaner.clean_and_transform(df)

    assert res.loc[0, "category"] == "Books"
    assert res.loc[0, "region"] == "South"
    assert res.loc[0, "product_id"] == "PRD-3"
    assert res.loc[0, "customer_id"] == "C-3"
    assert res.loc[0, "product_name"] == "Book"

    assert res.loc[1, "category"] == "Sports & Outdoors"
    assert res.loc[1, "region"] == "West"
