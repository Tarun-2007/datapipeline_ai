"""
DataPulse AI - Integration Tests for Dimensional Star Schema & Warehouse Analytics
"""
import pytest
import pandas as pd
from app.warehouse.loader import WarehouseLoader
from app.warehouse.analytics import WarehouseAnalytics
from app.warehouse.models import FactSales, DimProduct, DimCustomer, DimDate, StagingSales


def test_warehouse_loader_and_star_schema(db_session):
    """Verifies promotion from Silver staging into Gold dimensional star schema."""
    loader = WarehouseLoader(db_session)

    clean_df = pd.DataFrame([
        {
            "transaction_id": "TXN-WH-1",
            "transaction_date": pd.to_datetime("2024-02-10").date(),
            "product_id": "PRD-WH-1",
            "product_name": "Ultra Keyboard",
            "category": "Electronics",
            "quantity": 2,
            "unit_price": 75.0,
            "discount": 0.0,
            "net_sales": 150.0,
            "region": "North",
            "customer_id": "C-WH-1",
            "batch_id": "BATCH-WH-01"
        }
    ])

    # 1. Load Staging
    loader.load_staging_and_quarantine(
        batch_id="BATCH-WH-01",
        clean_df=clean_df,
        quarantine_records=[]
    )
    assert db_session.query(StagingSales).count() == 1

    # 2. Promote to Gold
    gold_stats = loader.load_warehouse_gold(batch_id="BATCH-WH-01")
    assert gold_stats["fact_sales_loaded"] == 1
    assert db_session.query(FactSales).count() == 1
    assert db_session.query(DimProduct).count() == 1
    assert db_session.query(DimCustomer).count() == 1
    assert db_session.query(DimDate).count() == 1

    # 3. Test Analytics KPIs
    kpis = WarehouseAnalytics.get_sales_kpis(db_session)
    assert kpis["total_revenue"] == 150.0
    assert kpis["total_transactions"] == 1
    assert kpis["average_order_value"] == 150.0


def test_warehouse_loading_idempotency(db_session):
    """Verifies rerunning the same batch does not create duplicate fact records."""
    loader = WarehouseLoader(db_session)
    clean_df = pd.DataFrame([
        {
            "transaction_id": "TXN-IDEMP-1",
            "transaction_date": pd.to_datetime("2024-02-11").date(),
            "product_id": "PRD-IDEMP-1",
            "product_name": "Monitor",
            "category": "Electronics",
            "quantity": 1,
            "unit_price": 300.0,
            "discount": 0.0,
            "net_sales": 300.0,
            "region": "East",
            "customer_id": "C-IDEMP-1",
            "batch_id": "BATCH-IDEMP-01"
        }
    ])

    loader.load_staging_and_quarantine("BATCH-IDEMP-01", clean_df, [])
    loader.load_warehouse_gold("BATCH-IDEMP-01")

    # Reload same batch
    loader.load_staging_and_quarantine("BATCH-IDEMP-01", clean_df, [])
    gold_stats_2 = loader.load_warehouse_gold("BATCH-IDEMP-01")

    # Second run should skip already loaded transaction without error
    assert gold_stats_2["fact_sales_loaded"] == 0
    assert db_session.query(FactSales).filter_by(transaction_id="TXN-IDEMP-1").count() == 1
