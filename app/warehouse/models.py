"""
DataPulse AI - Database Warehouse & Staging Models
Defines Bronze (raw metadata), Silver (staging/quarantine), and Gold (Star schema dimensional model) tables.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, Boolean, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.core.database import Base


# ==============================================================================
# BRONZE LAYER: Raw Batches & Ingestion Tracking
# ==============================================================================
class RawSalesBatch(Base):
    __tablename__ = "raw_sales_batches"

    batch_id = Column(String(64), primary_key=True, index=True)
    source = Column(String(50), nullable=False)  # 'csv', 'rest_api'
    source_uri = Column(String(255), nullable=True)
    row_count = Column(Integer, default=0)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    checksum = Column(String(64), nullable=True)
    status = Column(String(30), default="INGESTED")  # INGESTED, PROCESSED, FAILED

    staging_records = relationship("StagingSales", back_populates="batch", cascade="all, delete-orphan")
    pipeline_runs = relationship("PipelineRun", back_populates="batch")


# ==============================================================================
# SILVER LAYER: Staging & Data Quality Quarantine
# ==============================================================================
class StagingSales(Base):
    __tablename__ = "staging_sales"

    stg_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), ForeignKey("raw_sales_batches.batch_id"), nullable=False, index=True)
    transaction_id = Column(String(64), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    product_id = Column(String(32), nullable=False, index=True)
    product_name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    net_sales = Column(Float, nullable=False)
    region = Column(String(64), nullable=False, index=True)
    customer_id = Column(String(32), nullable=False, index=True)
    loaded_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("RawSalesBatch", back_populates="staging_records")


class DataQualityIssue(Base):
    """Quarantine table storing rejected records with diagnostic failure reasons."""
    __tablename__ = "data_quality_issues"

    issue_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), nullable=False, index=True)
    transaction_id = Column(String(64), nullable=True, index=True)
    rule_violated = Column(String(128), nullable=False, index=True)
    rejected_value = Column(String(255), nullable=True)
    rejection_reason = Column(Text, nullable=False)
    raw_payload = Column(Text, nullable=True)  # JSON string of the malformed record
    quarantined_at = Column(DateTime, default=datetime.utcnow)


# ==============================================================================
# GOLD LAYER: Dimensional Star Schema (Analytics Ready)
# ==============================================================================
class DimDate(Base):
    __tablename__ = "dim_date"

    date_key = Column(Integer, primary_key=True)  # YYYYMMDD
    full_date = Column(Date, unique=True, nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    day_name = Column(String(16), nullable=False)
    day_of_month = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    month_name = Column(String(16), nullable=False)
    quarter = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    is_weekend = Column(Boolean, default=False)


class DimProduct(Base):
    __tablename__ = "dim_product"

    product_id = Column(String(32), primary_key=True)
    product_name = Column(String(128), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)


class DimCustomer(Base):
    __tablename__ = "dim_customer"

    customer_id = Column(String(32), primary_key=True)
    region = Column(String(64), nullable=False, index=True)
    total_orders = Column(Integer, default=1)
    first_purchase_date = Column(Date, nullable=True)
    last_purchase_date = Column(Date, nullable=True)


class FactSales(Base):
    __tablename__ = "fact_sales"

    fact_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), unique=True, nullable=False, index=True)
    date_key = Column(Integer, ForeignKey("dim_date.date_key"), nullable=False, index=True)
    product_id = Column(String(32), ForeignKey("dim_product.product_id"), nullable=False, index=True)
    customer_id = Column(String(32), ForeignKey("dim_customer.customer_id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    net_sales = Column(Float, nullable=False)
    batch_id = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Composite index for time-series analytics
    __table_args__ = (
        Index("idx_fact_sales_date_product", "date_key", "product_id"),
    )


# ==============================================================================
# OPERATIONAL & ML MONITORING TABLES
# ==============================================================================
class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id = Column(String(64), primary_key=True)
    batch_id = Column(String(64), ForeignKey("raw_sales_batches.batch_id"), nullable=True)
    source = Column(String(50), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    records_ingested = Column(Integer, default=0)
    records_processed = Column(Integer, default=0)
    records_quarantined = Column(Integer, default=0)
    status = Column(String(30), default="RUNNING")  # RUNNING, SUCCESS, FAILED
    error_details = Column(Text, nullable=True)

    batch = relationship("RawSalesBatch", back_populates="pipeline_runs")


class SalesForecast(Base):
    __tablename__ = "sales_forecasts"

    forecast_id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=True)
    forecast_date = Column(Date, nullable=False, index=True)
    predicted_sales = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)
    model_type = Column(String(64), default="RandomForestRegressor")
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SalesAnomaly(Base):
    __tablename__ = "sales_anomalies"

    anomaly_id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_id = Column(String(64), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False, index=True)
    product_id = Column(String(32), nullable=False)
    category = Column(String(64), nullable=False)
    region = Column(String(64), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    net_sales = Column(Float, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, default=True)
    explanation = Column(Text, nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
