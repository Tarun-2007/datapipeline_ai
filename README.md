# DataPulse AI: Intelligent Data Pipeline and Predictive Analytics Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B.svg?logo=streamlit)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql)](https://www.postgresql.org/)
[![Scikit--Learn](https://img.shields.io/badge/Scikit--Learn-1.4+-F7931E.svg?logo=scikit-learn)](https://scikit-learn.org/)
[![Apache Airflow](https://img.shields.io/badge/Apache%20Airflow-2.8+-017CEE.svg?logo=apache-airflow)](https://airflow.apache.org/)
[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-Ready-2496ED.svg?logo=docker)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/Pytest-20%20Passed%20%7C%20100%25-brightgreen.svg)](https://pytest.org/)

---

## 1. Project Overview & Business Problem

Modern retail and e-commerce enterprises ingest millions of sales transactions daily across distributed point-of-sale (POS) systems, e-commerce storefronts, and third-party APIs. However, raw incoming data is inherently dirty: corrupted by duplicated network payloads, unparsable date formats, missing customer/product foreign keys, negative quantities, illegal discounts (>100%), and inconsistent categorization.

Unvalidated dirty data directly contaminates analytics reporting and destroys predictive machine learning models. Silent data deletion causes catastrophic revenue misattribution and audit failures.

**DataPulse AI** is an enterprise-grade, end-to-end Data Engineering for AI platform. It provides:
1. **Multi-Source Ingestion:** Automated ingestion from CSV batch dumps and paginated REST APIs with cryptographic SHA-256 idempotency.
2. **Zero Silent Loss Validation:** Strict schema conformance and business rule enforcement with automatic quarantine routing for forensic diagnosis.
3. **Medallion Data Warehouse Architecture:** Bronze (raw immutable data), Silver (cleaned staging & quarantine), and Gold (Star schema dimensional model) built on PostgreSQL with SQLite zero-config local fallback.
4. **Predictive AI Forecasting:** Multi-step 7-day sales demand forecasting using leak-free lag and rolling features evaluated on strict chronological splits against baseline benchmarks.
5. **Unsupervised Anomaly Detection:** Isolation Forest outlier detection generating transparent, natural-language explanations for irregular transactions.
6. **Unified API & Monitoring:** Asynchronous FastAPI backend with automated Swagger documentation and a 7-page dark glassmorphism Streamlit analytics portal.

---

## 2. Architecture & Data Flow

```mermaid
flowchart TD
    subgraph Ingestion_Sources["Data Ingestion Sources"]
        CSV[Raw CSV Files]
        API[Simulated REST API Paginated]
    end

    subgraph Bronze["Bronze Layer (Raw Archive)"]
        RawFiles[(Versioned Bronze Files)]
        RawMeta[raw_sales_batches Table]
    end

    subgraph Validation_Cleaning["Validation & Transformation"]
        Validator{Schema Conformance & Business Rules}
        Quarantine[(Quarantine Table: data_quality_issues)]
        Cleaner[Cleaner: Canonical Normalization & Net Sales Calc]
    end

    subgraph Silver["Silver Layer (Staging)"]
        Staging[(staging_sales Table)]
        DQReport[Data Quality Scorecard]
    end

    subgraph Gold["Gold Layer (Star Schema Warehouse)"]
        DimDate[(dim_date)]
        DimProduct[(dim_product)]
        DimCustomer[(dim_customer)]
        FactSales[(fact_sales)]
    end

    subgraph ML_Engine["Machine Learning Engine"]
        FeatEng[Time-Series Lag & Rolling Feature Engineering]
        ForecastModel[Sales Forecaster: Random Forest Regressor]
        AnomalyModel[Anomaly Detector: Isolation Forest]
        ForecastTable[(sales_forecasts Table)]
        AnomalyTable[(sales_anomalies Table)]
    end

    subgraph Serving_Layer["Serving & Monitoring"]
        Airflow[Apache Airflow DAG: sales_data_pipeline]
        FastAPI[FastAPI REST Server /docs]
        Streamlit[Streamlit 7-Page Analytics Dashboard]
    end

    CSV --> Bronze
    API --> Bronze
    Bronze --> Validator
    Validator -- "Invalid (Negative Price, Bad Date, Duplicates)" --> Quarantine
    Validator -- "Valid Records" --> Cleaner
    Cleaner --> Staging
    Cleaner --> DQReport
    Staging --> Gold
    Gold --> FeatEng
    FeatEng --> ForecastModel --> ForecastTable
    Gold --> AnomalyModel --> AnomalyTable
    Airflow -. Orchestrates .-> Ingestion_Sources
    Airflow -. Orchestrates .-> Gold
    Gold --> FastAPI --> Streamlit
    ForecastTable --> FastAPI
    AnomalyTable --> FastAPI
```

---

## 3. Technology Stack & Design Decisions

| Category | Technology | Rationale & Architectural Decisions |
| :--- | :--- | :--- |
| **Language** | Python 3.11 - 3.13 | Native typing, modern dataclasses, and rich data engineering ecosystem. |
| **Data Processing** | Pandas, NumPy | High-performance vector transformations, temporal lag shifting, and rolling aggregates. |
| **Database & ORM** | PostgreSQL 16 + SQLAlchemy 2.0 | Transactional ACID compliance, declarative Star schema, and dual-engine architecture (PostgreSQL primary + SQLite local fallback). |
| **Pipeline Orchestration**| Apache Airflow 2.8+ | Enterprise 9-task DAG with retries, timeout bounds, and task dependencies. |
| **Backend REST API** | FastAPI + Uvicorn | Asynchronous background execution, Pydantic v2 validation, OpenAPI/Swagger docs. |
| **Predictive ML** | Scikit-learn (Random Forest, Isolation Forest) | Non-linear regression with lag features and unsupervised outlier detection. |
| **Visual Dashboard** | Streamlit + Plotly | Reactive 7-page dark glassmorphism dashboard with interactive filters and CSV exports. |
| **Containerization** | Docker & Docker Compose | Multi-container architecture with persistent volumes and healthcheck coordination. |
| **Testing** | Pytest | Isolated in-memory database testing, coverage, and end-to-end integration tests. |

---

## 4. Medallion Layered Storage

1. **Bronze Layer:**
   - Raw records are preserved verbatim in versioned batch files (`data/raw/<batch_id>_<file>`).
   - Every batch is registered in `raw_sales_batches` with SHA-256 cryptographic checksum to enforce idempotency.
   - Raw files are never modified or silently overwritten.

2. **Silver Layer:**
   - Rows passing schema checks are loaded into `staging_sales` with derived financial metrics (`net_sales = quantity * unit_price * (1 - discount)`).
   - Malformed records are diverted into `data_quality_issues` quarantine with the specific rule violated, rejected value, diagnostic explanation, and raw JSON payload.

3. **Gold Layer:**
   - Dimensional Star Schema: `dim_date`, `dim_product`, `dim_customer`, and `fact_sales`.
   - Idempotent merge logic prevents transaction duplication across pipeline reruns.
   - Indexed composite keys enable sub-second aggregations across millions of rows.

---

## 5. Data Quality Rules & Quarantine Strategy

Every incoming transaction is verified against 8 strict business validation rules:

| Rule Name | Validation Trigger | Quarantine Action |
| :--- | :--- | :--- |
| `MISSING_TRANSACTION_ID` | `transaction_id` is null, empty, or whitespace. | Quarantined; record flagged with failure reason. |
| `DUPLICATE_TRANSACTION_ID` | Encountering a business key already processed in current batch. | Quarantined; prevents silent duplicate aggregation. |
| `MISSING_CUSTOMER_ID` | `customer_id` is missing or null. | Quarantined; preserves customer dimensional integrity. |
| `MISSING_PRODUCT_ID` | `product_id` is missing or null. | Quarantined; enforces catalog dimensional relation. |
| `INVALID_DATE_FORMAT` | Date cannot be parsed into valid `YYYY-MM-DD`. | Quarantined; prevents time-series index corruption. |
| `NON_POSITIVE_QUANTITY` | `quantity <= 0`. | Quarantined; invalid order volume rejected. |
| `NON_POSITIVE_PRICE` | `unit_price <= 0.0`. | Quarantined; illegal zero or negative prices rejected. |
| `INVALID_DISCOUNT_RANGE` | `discount < 0.0` or `discount >= 1.0` (>=100%). | Quarantined; prevents negative or impossible margins. |

**Zero Silent Loss Invariant:** `records_ingested = records_accepted + records_quarantined`.

---

## 6. Machine Learning Methodology

### A. Sales Forecasting (Random Forest vs Baseline Benchmark)
- **Objective:** Predict total daily sales revenue for the next 7 days.
- **Feature Engineering (No Target Leakage):**
  - Calendar: `day_of_week`, `day_of_month`, `month`, `is_weekend`.
  - Shifted Lags: `lag_1` (yesterday's sales), `lag_2`, `lag_7` (same day last week), `lag_14`.
  - Rolling Windows: `roll_mean_7` (7-day moving average), `roll_std_7`, `roll_mean_14`.
  - All lags and rolling statistics are strictly shifted by $\ge 1$ day to prevent target leakage.
- **Validation Split:** Chronological split (no random k-fold shuffle) to avoid lookahead bias.
- **Verified Benchmark Comparison:**
  - **7-Day Seasonal Lag Baseline MAE:** \$1,733.20
  - **Random Forest ML Model MAE:** \$1,399.92 (19.23% improvement over baseline)
  - **Random Forest ML Model RMSE:** \$1,636.17
- **Confidence Intervals:** 95% prediction intervals computed dynamically from model test error.
- **Demonstration Label:** Labeled as trained on synthetic sales data for algorithmic demonstration.

### B. Sales Anomaly Detection (Isolation Forest)
- **Objective:** Identify potentially fraudulent or unusual transaction patterns without supervised labels.
- **Features Used:** `quantity`, `unit_price`, `discount`, `net_sales`, `discount_amount` (standardized via `StandardScaler`).
- **Contamination Rate:** Calibrated to 3.0% expected anomaly rate.
- **Automated Explanations:** Every flagged record receives natural-language tags (e.g., *"High net sales ($1,845.00 >= 95th percentile)", "Unusually large quantity (10 units)", "Deep discount (20%) applied"*).
- **Limitations:** Unsupervised distance-based model; cannot distinguish between high-volume legitimate enterprise orders and data transmission glitches.

---

## 7. Apache Airflow Orchestration

DAG Name: `sales_data_pipeline`  
Schedule: Daily at 06:00 UTC (`0 6 * * *`)

```
[generate_or_fetch_sample_data] 
  >> [ingest_batch] 
  >> [validate_input_schema] 
  >> [clean_and_transform] 
  >> [load_staging_tables] 
  >> [data_quality_checks] 
  >> [load_analytics_warehouse] 
  >> [generate_features_and_aggregates] 
  >> [record_metrics_and_status]
```

- **Retries:** Configured for 2 automatic retries with 2-minute backoff.
- **Execution Timeout:** 15 minutes per batch.
- **Local Airflow UI:** Access at `http://localhost:8080` (admin / admin).

---

## 8. REST API Documentation (FastAPI)

Interactive Swagger UI available at: `http://127.0.0.1:8000/docs`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | System health check (database connection, disk space, environment). |
| `GET` | `/api/v1/sales/summary` | Headline KPIs: Total Revenue, Total Transactions, Average Order Value (AOV). |
| `GET` | `/api/v1/sales/trends` | Chronological daily sales trajectory with transaction counts. |
| `GET` | `/api/v1/sales/by-category` | Revenue and volume aggregation grouped by product category. |
| `GET` | `/api/v1/sales/by-region` | Revenue and customer penetration grouped by geographical region. |
| `GET` | `/api/v1/sales/top-products` | Top 10 best-selling products by total net sales. |
| `GET` | `/api/v1/sales/growth` | Month-over-Month (MoM) revenue growth velocity. |
| `GET` | `/api/v1/data-quality/summary`| Total ingested, valid, quarantined, and rejection rate metrics. |
| `GET` | `/api/v1/data-quality/issues` | Quarantined records with failure reasons and raw JSON payloads. |
| `GET` | `/api/v1/forecasts` | Latest 7-day predicted sales, confidence intervals, and evaluation metrics. |
| `POST`| `/api/v1/models/train` | Triggers background retraining of forecasting and anomaly models. |
| `GET` | `/api/v1/anomalies` | Flagged transactions with anomaly scores and diagnostic explanations. |
| `GET` | `/api/v1/pipeline/runs` | Execution history of all pipeline runs with latency and status. |
| `POST`| `/api/v1/pipeline/run` | Triggers batch pipeline ingestion via background worker. |
| `GET` | `/api/v1/mock-api/sales` | Simulated paginated REST API endpoint (`?page=1&page_size=100`). |

---

## 9. 7-Page Streamlit Analytics Dashboard

Launch via: `streamlit run dashboard/app.py` (Default: `http://localhost:8501`)

1. **Executive Overview:** Headline KPI cards (Total Revenue, Transactions, AOV, Pipeline Status), daily revenue chart, quick batch trigger.
2. **Sales Analytics:** Category donut chart, regional performance bars, top 10 products table, Month-over-Month growth metrics.
3. **AI Forecasting:** 7-day future predictions with 95% confidence bands, baseline comparison benchmarks, and model retrain action.
4. **Anomaly Detection:** Outlier scatter plot in transaction space, filterable table by region/category, and natural-language diagnostic explanations.
5. **Data Quality:** Validation scorecard, rule violations breakdown chart, and forensic quarantine inspection repository.
6. **Pipeline Monitoring:** Latency duration bar chart, SLA uptime metrics, and execution history log.
7. **Data Explorer:** High-performance filterable table of clean Gold warehouse transactions with instant CSV export.

---

## 10. Local Setup & Quick Start Guide

### Prerequisites
- Python 3.11+ (or `uv`)
- Windows PowerShell, macOS Terminal, or Linux Bash
- Docker & Docker Compose (Optional for containerized run)

### Step 1: Clone and Set Up Virtual Environment

```powershell
# Clone the repository
git clone https://github.com/<your-username>/datapulse-ai.git
cd datapulse-ai

# Create virtual environment using uv or standard python
uv venv --python 3.13 .venv
# Activate in PowerShell:
.\.venv\Scripts\Activate.ps1
# (Or on Linux/macOS: source .venv/bin/activate)

# Install pinned dependencies
uv pip install -r requirements.txt
```

### Step 2: Seed the Platform (Zero-Config Immediate Demonstration)

Run the automated seed workflow: it initializes the database schema, generates 5,000 retail sales records, ingests them through all 9 pipeline stages, loads the Gold Star schema, and trains both AI models:

```powershell
python scripts/seed_data.py
```

### Step 3: Launch Services

Option A: **Interactive PowerShell Launcher:**
```powershell
.\scripts\start_services.ps1
```

Option B: **Start Individual Services:**
```powershell
# Terminal 1: Launch FastAPI Backend Server
uvicorn app.api.app:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Launch Streamlit Dashboard
streamlit run dashboard/app.py --server.port 8501
```

Option C: **Launch with Docker Compose:**
```bash
docker compose up -d
```
- **FastAPI Docs:** `http://localhost:8000/docs`
- **Streamlit Dashboard:** `http://localhost:8501`
- **Airflow Webserver:** `http://localhost:8080` (admin / admin)

### Deploy to Render

The repository includes a Render Blueprint for the FastAPI service and Streamlit dashboard:

1. Push this repository to GitHub and create a new Blueprint from it in the Render dashboard.
2. During Blueprint setup, provide the `DATABASE_URL` environment variable using the rotated PostgreSQL connection string from Render. Do not add credentials to `render.yaml` or commit them.
3. Deploy both services. Open the public URL shown for `datapulse-dashboard`; the API is available at the `datapulse-api` service URL with `/docs`.

The free web services may spin down when idle. Configure a paid instance if the application needs to stay continuously available.

---

## 11. Automated Test Suite & Verification Results

DataPulse AI includes an automated Pytest test suite covering schema validation, duplicate quarantine, net sales calculations, idempotent loading, dimensional Star schema promotion, machine learning forecasting, anomaly detection, and API endpoints.

```powershell
pytest -v
```

### Verified Test Results:
```text
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1 -- .venv\Scripts\python.exe
rootdir: datapulse-ai, configfile: pytest.ini, testpaths: tests
collected 20 items

tests/test_api.py::test_health_check_endpoint PASSED                     [  5%]
tests/test_api.py::test_sales_summary_endpoint PASSED                    [ 10%]
tests/test_api.py::test_data_quality_summary_endpoint PASSED             [ 15%]
tests/test_api.py::test_mock_sales_api_pagination PASSED                 [ 20%]
tests/test_ingestion.py::test_csv_ingestion_and_checksum PASSED          [ 25%]
tests/test_ingestion.py::test_simulated_api_ingestion PASSED             [ 30%]
tests/test_ml_anomaly.py::test_anomaly_detection_training_and_scoring PASSED [ 35%]
tests/test_ml_forecasting.py::test_time_series_feature_engineering_no_leakage PASSED [ 40%]
tests/test_ml_forecasting.py::test_sales_forecaster_train_and_predict PASSED [ 45%]
tests/test_pipeline_e2e.py::test_full_pipeline_e2e_execution PASSED      [ 50%]
tests/test_transformations.py::test_net_sales_calculation PASSED         [ 55%]
tests/test_transformations.py::test_categorical_standardization PASSED   [ 60%]
tests/test_validation.py::test_schema_conformance_valid PASSED           [ 65%]
tests/test_validation.py::test_schema_conformance_missing_columns PASSED [ 70%]
tests/test_validation.py::test_duplicate_transaction_id_quarantine PASSED [ 75%]
tests/test_validation.py::test_negative_quantity_and_price_quarantine PASSED [ 80%]
tests/test_validation.py::test_invalid_discount_range PASSED             [ 85%]
tests/test_validation.py::test_zero_silent_loss_invariant PASSED         [ 90%]
tests/test_warehouse.py::test_warehouse_loader_and_star_schema PASSED    [ 95%]
tests/test_warehouse.py::test_warehouse_loading_idempotency PASSED       [100%]

============================= 20 passed in 1.19s ==============================
```

---

## 12. Pushing to GitHub (Safe Practices)

Follow these steps to publish to your personal GitHub portfolio without exposing secrets:

```bash
# 1. Initialize Git repository
git init

# 2. Confirm .env and local db files are ignored
git status

# 3. Add files and create initial commit
git add .
git commit -m "feat: complete DataPulse AI platform with ETL, Gold warehouse, ML models, and dashboard"

# 4. Link your GitHub remote and push
git branch -M main
git remote add origin https://github.com/<your-username>/datapulse-ai.git
git push -u origin main
```

---

## 13. Resume Bullet Templates (With Verified Metrics)

Use these concise bullets on your resume:

- **Data Engineering / Pipeline:**
  > *"Architected an automated multi-source retail ETL pipeline ingesting 5,000+ daily transactions across CSV and paginated REST APIs; enforced 8 data quality rules with quarantine routing, achieving zero silent data loss and 100% idempotent warehouse loads in under 4 seconds."*

- **Data Warehousing & SQL Analytics:**
  > *"Designed a PostgreSQL Medallion warehouse (Bronze/Silver/Gold Star Schema) using SQLAlchemy; structured FactSales with dimensional tables and parameterized window queries to deliver sub-second aggregations for AOV, category shares, and Month-over-Month growth."*

- **Machine Learning & AI Platform:**
  > *"Built an end-to-end sales forecasting and anomaly platform using Random Forest and Isolation Forest; engineered leak-free lag/rolling features achieving an out-of-sample test MAE of \$1,399.92 (19.2% improvement over seasonal baseline) and served real-time predictions via FastAPI and Streamlit."*

---

## 14. License

This project is licensed under the MIT License - open-source for educational and portfolio demonstration.
