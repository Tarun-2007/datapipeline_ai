-- ==============================================================================
-- DataPulse AI - PostgreSQL Analytical Warehouse DDL Schema
-- Layers: Bronze (Raw Batches) -> Silver (Staging & Quarantine) -> Gold (Star Schema)
-- ==============================================================================

-- -----------------------------------------------------------------------------
-- 1. BRONZE LAYER: Raw Ingestion Tracking
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw_sales_batches (
    batch_id VARCHAR(64) PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_uri VARCHAR(255),
    row_count INTEGER DEFAULT 0,
    ingested_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    checksum VARCHAR(64),
    status VARCHAR(30) DEFAULT 'INGESTED'
);

CREATE INDEX IF NOT EXISTS idx_raw_batches_ingested ON raw_sales_batches(ingested_at);

-- -----------------------------------------------------------------------------
-- 2. SILVER LAYER: Staging & Data Quality Quarantine
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging_sales (
    stg_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) REFERENCES raw_sales_batches(batch_id) ON DELETE CASCADE,
    transaction_id VARCHAR(64) NOT NULL,
    transaction_date DATE NOT NULL,
    product_id VARCHAR(32) NOT NULL,
    product_name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    discount NUMERIC(6, 4) DEFAULT 0.0,
    net_sales NUMERIC(12, 2) NOT NULL,
    region VARCHAR(64) NOT NULL,
    customer_id VARCHAR(32) NOT NULL,
    loaded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staging_batch_id ON staging_sales(batch_id);
CREATE INDEX IF NOT EXISTS idx_staging_txn_id ON staging_sales(transaction_id);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id SERIAL PRIMARY KEY,
    batch_id VARCHAR(64) NOT NULL,
    transaction_id VARCHAR(64),
    rule_violated VARCHAR(128) NOT NULL,
    rejected_value VARCHAR(255),
    rejection_reason TEXT NOT NULL,
    raw_payload TEXT,
    quarantined_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dq_batch_id ON data_quality_issues(batch_id);
CREATE INDEX IF NOT EXISTS idx_dq_rule ON data_quality_issues(rule_violated);

-- -----------------------------------------------------------------------------
-- 3. GOLD LAYER: Dimensional Star Schema
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY, -- YYYYMMDD
    full_date DATE UNIQUE NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name VARCHAR(16) NOT NULL,
    day_of_month INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name VARCHAR(16) NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    is_weekend BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS dim_product (
    product_id VARCHAR(32) PRIMARY KEY,
    product_name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    first_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dim_product_cat ON dim_product(category);

CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id VARCHAR(32) PRIMARY KEY,
    region VARCHAR(64) NOT NULL,
    total_orders INTEGER DEFAULT 1,
    first_purchase_date DATE,
    last_purchase_date DATE
);

CREATE INDEX IF NOT EXISTS idx_dim_customer_reg ON dim_customer(region);

CREATE TABLE IF NOT EXISTS fact_sales (
    fact_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
    product_id VARCHAR(32) NOT NULL REFERENCES dim_product(product_id),
    customer_id VARCHAR(32) NOT NULL REFERENCES dim_customer(customer_id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    discount NUMERIC(6, 4) DEFAULT 0.0,
    net_sales NUMERIC(12, 2) NOT NULL,
    batch_id VARCHAR(64) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date ON fact_sales(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product ON fact_sales(product_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer ON fact_sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_fact_sales_date_prod ON fact_sales(date_key, product_id);

-- -----------------------------------------------------------------------------
-- 4. OPERATIONAL MONITORING & ML TABLES
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id VARCHAR(64) PRIMARY KEY,
    batch_id VARCHAR(64) REFERENCES raw_sales_batches(batch_id),
    source VARCHAR(50) NOT NULL,
    start_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    duration_seconds NUMERIC(8, 2),
    records_ingested INTEGER DEFAULT 0,
    records_processed INTEGER DEFAULT 0,
    records_quarantined INTEGER DEFAULT 0,
    status VARCHAR(30) DEFAULT 'RUNNING',
    error_details TEXT
);

CREATE TABLE IF NOT EXISTS sales_forecasts (
    forecast_id SERIAL PRIMARY KEY,
    run_id VARCHAR(64),
    forecast_date DATE NOT NULL,
    predicted_sales NUMERIC(12, 2) NOT NULL,
    lower_bound NUMERIC(12, 2),
    upper_bound NUMERIC(12, 2),
    model_type VARCHAR(64) DEFAULT 'RandomForestRegressor',
    mae NUMERIC(10, 2),
    rmse NUMERIC(10, 2),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_anomalies (
    anomaly_id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(64) NOT NULL,
    transaction_date DATE NOT NULL,
    product_id VARCHAR(32) NOT NULL,
    category VARCHAR(64) NOT NULL,
    region VARCHAR(64) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    net_sales NUMERIC(12, 2) NOT NULL,
    anomaly_score NUMERIC(8, 4) NOT NULL,
    is_anomaly BOOLEAN DEFAULT TRUE,
    explanation TEXT NOT NULL,
    detected_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
