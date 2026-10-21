"""
DataPulse AI - Unit Tests for Data Validation & Quarantine Engine
"""
import pytest
import pandas as pd
from app.transformations.validator import DataValidator, REQUIRED_COLUMNS


def test_schema_conformance_valid():
    """Verifies complete valid schema passes validation."""
    df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    validator = DataValidator(batch_id="TEST-VAL-01")
    is_valid, missing = validator.validate_schema(df)
    assert is_valid is True
    assert len(missing) == 0


def test_schema_conformance_missing_columns():
    """Verifies missing required columns are properly detected."""
    df = pd.DataFrame({"transaction_id": ["TXN-1"], "quantity": [1]})
    validator = DataValidator(batch_id="TEST-VAL-02")
    is_valid, missing = validator.validate_schema(df)
    assert is_valid is False
    assert "transaction_date" in missing
    assert "unit_price" in missing


def test_duplicate_transaction_id_quarantine():
    """Verifies duplicate transaction IDs on business key are quarantined without silent deletion."""
    records = [
        {"transaction_id": "TXN-DUP-1", "transaction_date": "2024-03-01", "product_id": "PRD-1", "product_name": "Widget", "category": "Electronics", "quantity": 1, "unit_price": 50.0, "discount": 0.0, "region": "North", "customer_id": "C-1"},
        {"transaction_id": "TXN-DUP-1", "transaction_date": "2024-03-01", "product_id": "PRD-1", "product_name": "Widget", "category": "Electronics", "quantity": 1, "unit_price": 50.0, "discount": 0.0, "region": "North", "customer_id": "C-1"},
    ]
    df = pd.DataFrame(records)
    validator = DataValidator(batch_id="TEST-VAL-03")
    res = validator.validate_and_quarantine(df)

    assert res.total_input == 2
    assert res.accepted_count == 1
    assert res.rejected_count == 1
    assert res.duplicate_count == 1
    assert res.quarantine_records[0]["rule_violated"] == "DUPLICATE_TRANSACTION_ID"


def test_negative_quantity_and_price_quarantine():
    """Verifies negative quantities and prices are quarantined."""
    records = [
        {"transaction_id": "TXN-NEG-1", "transaction_date": "2024-03-01", "product_id": "PRD-1", "product_name": "Widget", "category": "Electronics", "quantity": -3, "unit_price": 50.0, "discount": 0.0, "region": "North", "customer_id": "C-1"},
        {"transaction_id": "TXN-NEG-2", "transaction_date": "2024-03-01", "product_id": "PRD-2", "product_name": "Gadget", "category": "Electronics", "quantity": 2, "unit_price": -20.0, "discount": 0.0, "region": "South", "customer_id": "C-2"},
    ]
    df = pd.DataFrame(records)
    validator = DataValidator(batch_id="TEST-VAL-04")
    res = validator.validate_and_quarantine(df)

    assert res.accepted_count == 0
    assert res.rejected_count == 2
    rules = [q["rule_violated"] for q in res.quarantine_records]
    assert "NON_POSITIVE_QUANTITY" in rules
    assert "NON_POSITIVE_PRICE" in rules


def test_invalid_discount_range():
    """Verifies illegal discount values (> 1.0 or < 0.0) are quarantined."""
    records = [
        {"transaction_id": "TXN-DISC-1", "transaction_date": "2024-03-01", "product_id": "PRD-1", "product_name": "Widget", "category": "Electronics", "quantity": 1, "unit_price": 50.0, "discount": 1.5, "region": "North", "customer_id": "C-1"},
        {"transaction_id": "TXN-DISC-2", "transaction_date": "2024-03-01", "product_id": "PRD-2", "product_name": "Gadget", "category": "Electronics", "quantity": 1, "unit_price": 50.0, "discount": -0.2, "region": "North", "customer_id": "C-2"},
    ]
    df = pd.DataFrame(records)
    validator = DataValidator(batch_id="TEST-VAL-05")
    res = validator.validate_and_quarantine(df)

    assert res.accepted_count == 0
    assert res.rejected_count == 2
    for q in res.quarantine_records:
        assert q["rule_violated"] == "INVALID_DISCOUNT_RANGE"


def test_zero_silent_loss_invariant():
    """Mathematical guarantee: accepted + quarantined must always equal total input."""
    gen = DataValidator(batch_id="TEST-VAL-06")
    from app.ingestion.generator import SalesDataGenerator
    df = SalesDataGenerator(seed=99).generate_records(num_records=200, dirty_rate=0.15)
    res = gen.validate_and_quarantine(df)

    assert (res.accepted_count + res.rejected_count) == len(df)
