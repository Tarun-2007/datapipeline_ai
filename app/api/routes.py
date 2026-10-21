"""
DataPulse AI - REST API Route Definitions
Exposes analytical warehouse queries, pipeline orchestrations, model training, and simulated ingestion endpoints.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
import pandas as pd

from app.core.database import get_db
from app.core.logging import logger
from app.warehouse.models import PipelineRun, DataQualityIssue, SalesForecast, SalesAnomaly, FactSales, DimDate
from app.warehouse.analytics import WarehouseAnalytics
from app.monitoring.metrics import PlatformMonitor
from app.ingestion.pipeline import SalesDataPipeline
from app.ml.forecasting import SalesForecaster
from app.ml.anomaly import SalesAnomalyDetector

router = APIRouter()

# Global background job status cache
JOB_STATUS: Dict[str, Any] = {
    "pipeline_running": False,
    "last_pipeline_result": None,
    "training_running": False,
    "last_training_result": None
}


def _run_pipeline_background(source_type: str, file_path: Optional[str] = None):
    """Background task worker for pipeline ingestion."""
    global JOB_STATUS
    JOB_STATUS["pipeline_running"] = True
    try:
        with SalesDataPipeline() as pipeline:
            result = pipeline.run_pipeline(source_type=source_type, file_path=file_path)
            JOB_STATUS["last_pipeline_result"] = result
    except Exception as e:
        logger.error(f"Background pipeline failed: {e}")
        JOB_STATUS["last_pipeline_result"] = {"status": "FAILED", "error": str(e)}
    finally:
        JOB_STATUS["pipeline_running"] = False


def _train_models_background():
    """Background task worker for training ML models and persisting predictions."""
    global JOB_STATUS
    JOB_STATUS["training_running"] = True
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            # 1. Train forecasting model
            daily_data = WarehouseAnalytics.get_daily_revenue(db)
            if len(daily_data) >= 15:
                daily_df = pd.DataFrame(daily_data)
                forecaster = SalesForecaster()
                fc_metrics = forecaster.train_and_evaluate(daily_df)
                forecasts = forecaster.predict_next_7_days(daily_df)

                # Store forecasts in warehouse
                db.query(SalesForecast).delete()
                for fc in forecasts:
                    sf = SalesForecast(
                        forecast_date=pd.to_datetime(fc["forecast_date"]).date(),
                        predicted_sales=fc["predicted_sales"],
                        lower_bound=fc["lower_bound"],
                        upper_bound=fc["upper_bound"],
                        model_type=fc["model_type"],
                        mae=fc_metrics.get("ml_model", {}).get("mae"),
                        rmse=fc_metrics.get("ml_model", {}).get("rmse")
                    )
                    db.add(sf)
                db.commit()

            # 2. Train anomaly detector and flag records
            recent_txns = WarehouseAnalytics.get_recent_transactions(db, limit=5000)
            if len(recent_txns) >= 50:
                txns_df = pd.DataFrame(recent_txns)
                detector = SalesAnomalyDetector()
                det_metrics = detector.train(txns_df)
                scored_df = detector.detect_anomalies(txns_df)

                # Store anomalies in warehouse
                anomalies_only = scored_df[scored_df["is_anomaly"]].copy()
                db.query(SalesAnomaly).delete()
                for _, a_row in anomalies_only.iterrows():
                    anom = SalesAnomaly(
                        transaction_id=str(a_row["transaction_id"]),
                        transaction_date=pd.to_datetime(a_row["transaction_date"]).date(),
                        product_id=str(a_row["product_id"]),
                        category=str(a_row["category"]),
                        region=str(a_row["region"]),
                        quantity=int(a_row["quantity"]),
                        unit_price=float(a_row["unit_price"]),
                        net_sales=float(a_row["net_sales"]),
                        anomaly_score=float(a_row["anomaly_score"]),
                        is_anomaly=True,
                        explanation=str(a_row["explanation"])
                    )
                    db.add(anom)
                db.commit()

            JOB_STATUS["last_training_result"] = {
                "status": "SUCCESS",
                "forecasting": fc_metrics if 'fc_metrics' in locals() else "Insufficient data",
                "anomaly": det_metrics if 'det_metrics' in locals() else "Insufficient data"
            }
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Background model training failed: {e}")
        JOB_STATUS["last_training_result"] = {"status": "FAILED", "error": str(e)}
    finally:
        JOB_STATUS["training_running"] = False


# ==============================================================================
# PIPELINE ENDPOINTS
# ==============================================================================
@router.get("/pipeline/runs")
def list_pipeline_runs(limit: int = 50, db: Session = Depends(get_db)):
    """Fetches chronological pipeline execution audit history."""
    return PlatformMonitor.get_pipeline_runs_history(db, limit=limit)


@router.post("/pipeline/run")
def trigger_pipeline_run(
    source_type: str = Query("csv", description="Source type: 'csv', 'api', or 'simulated_api'"),
    file_path: Optional[str] = Query(None, description="Optional path to raw CSV"),
    run_async: bool = Query(True, description="Execute in background or synchronously"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Triggers an end-to-end data pipeline ingestion and warehousing job."""
    global JOB_STATUS
    if JOB_STATUS["pipeline_running"]:
        return {"status": "BUSY", "message": "A pipeline run is currently in progress."}

    if run_async and background_tasks:
        background_tasks.add_task(_run_pipeline_background, source_type, file_path)
        return {
            "status": "QUEUED",
            "message": f"Pipeline ingestion queued for source '{source_type}'. Monitor progress at /api/v1/pipeline/runs."
        }
    else:
        with SalesDataPipeline(db=db) as pipeline:
            result = pipeline.run_pipeline(source_type=source_type, file_path=file_path)
            return {"status": "COMPLETED", "result": result}


# ==============================================================================
# DATA QUALITY ENDPOINTS
# ==============================================================================
@router.get("/data-quality/summary")
def get_data_quality_summary(db: Session = Depends(get_db)):
    """Returns data quality health scorecards, violation counts, and quarantine rates."""
    return WarehouseAnalytics.get_data_quality_metrics(db)


@router.get("/data-quality/issues")
def get_data_quality_issues(limit: int = 100, rule: Optional[str] = None, db: Session = Depends(get_db)):
    """Retrieves quarantined invalid records with rejection diagnostics."""
    query = db.query(DataQualityIssue)
    if rule:
        query = query.filter(DataQualityIssue.rule_violated == rule)
    issues = query.order_by(DataQualityIssue.issue_id.desc()).limit(limit).all()

    return [{
        "issue_id": i.issue_id,
        "batch_id": i.batch_id,
        "transaction_id": i.transaction_id,
        "rule_violated": i.rule_violated,
        "rejected_value": i.rejected_value,
        "rejection_reason": i.rejection_reason,
        "raw_payload": i.raw_payload,
        "quarantined_at": i.quarantined_at.isoformat() if i.quarantined_at else None
    } for i in issues]


# ==============================================================================
# SALES ANALYTICS ENDPOINTS
# ==============================================================================
@router.get("/sales/summary")
def get_sales_summary(db: Session = Depends(get_db)):
    """Returns headline KPIs: Revenue, Transactions, AOV, and customer metrics."""
    return WarehouseAnalytics.get_sales_kpis(db)


@router.get("/sales/trends")
def get_sales_trends(db: Session = Depends(get_db)):
    """Returns chronological daily revenue and order trends."""
    return WarehouseAnalytics.get_daily_revenue(db)


@router.get("/sales/by-category")
def get_sales_by_category(db: Session = Depends(get_db)):
    """Returns sales breakdown by product category."""
    return WarehouseAnalytics.get_revenue_by_category(db)


@router.get("/sales/by-region")
def get_sales_by_region(db: Session = Depends(get_db)):
    """Returns sales breakdown and customer coverage by region."""
    return WarehouseAnalytics.get_revenue_by_region(db)


@router.get("/sales/top-products")
def get_top_products(limit: int = 10, db: Session = Depends(get_db)):
    """Returns best-selling products by net revenue."""
    return WarehouseAnalytics.get_top_products(db, limit=limit)


@router.get("/sales/growth")
def get_sales_growth(db: Session = Depends(get_db)):
    """Returns Month-over-Month (MoM) revenue growth velocity."""
    return WarehouseAnalytics.get_sales_growth(db)


@router.get("/sales/transactions")
def get_transactions(
    limit: int = 100,
    region: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Filterable query for granular transactions."""
    return WarehouseAnalytics.get_recent_transactions(db, limit=limit, region=region, category=category)


# ==============================================================================
# MACHINE LEARNING & PREDICTION ENDPOINTS
# ==============================================================================
@router.get("/forecasts")
def get_forecasts(db: Session = Depends(get_db)):
    """Returns the latest 7-day sales forecasts and model evaluation benchmarks."""
    forecasts = db.query(SalesForecast).order_by(SalesForecast.forecast_date.asc()).all()
    if not forecasts:
        # Generate on demand if available
        daily_data = WarehouseAnalytics.get_daily_revenue(db)
        if len(daily_data) >= 20:
            forecaster = SalesForecaster()
            daily_df = pd.DataFrame(daily_data)
            metrics = forecaster.train_and_evaluate(daily_df)
            preds = forecaster.predict_next_7_days(daily_df)
            return {
                "forecasts": preds,
                "metrics": metrics,
                "status": "GENERATED_ON_THE_FLY"
            }
        return {
            "forecasts": [],
            "metrics": {},
            "status": "NOT_ENOUGH_DATA",
            "message": "Minimum 20 days of sales data required for forecasting."
        }

    first = forecasts[0]
    return {
        "forecasts": [{
            "forecast_date": str(f.forecast_date),
            "predicted_sales": f.predicted_sales,
            "lower_bound": f.lower_bound,
            "upper_bound": f.upper_bound,
            "model_type": f.model_type
        } for f in forecasts],
        "metrics": {
            "mae": first.mae,
            "rmse": first.rmse,
            "model_type": first.model_type
        },
        "status": "PERSISTED"
    }


@router.post("/models/train")
def train_models(
    background_tasks: BackgroundTasks,
    run_async: bool = Query(True)
):
    """Triggers retraining of both Forecasting and Anomaly Detection models."""
    global JOB_STATUS
    if JOB_STATUS["training_running"]:
        return {"status": "BUSY", "message": "Model training is already running in background."}

    if run_async:
        background_tasks.add_task(_train_models_background)
        return {"status": "QUEUED", "message": "Model training task queued in background."}
    else:
        _train_models_background()
        return {"status": "COMPLETED", "result": JOB_STATUS["last_training_result"]}


@router.get("/models/status")
def get_models_status():
    """Returns training background job status and cached model metrics."""
    return JOB_STATUS


@router.get("/anomalies")
def get_anomalies(
    limit: int = 100,
    region: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Returns flagged sales anomalies with anomaly scores and diagnostic explanations."""
    query = db.query(SalesAnomaly).filter(SalesAnomaly.is_anomaly == True)
    if region and region != "All":
        query = query.filter(SalesAnomaly.region == region)
    if category and category != "All":
        query = query.filter(SalesAnomaly.category == category)

    anomalies = query.order_by(SalesAnomaly.anomaly_score.desc()).limit(limit).all()

    return [{
        "anomaly_id": a.anomaly_id,
        "transaction_id": a.transaction_id,
        "transaction_date": str(a.transaction_date),
        "product_id": a.product_id,
        "category": a.category,
        "region": a.region,
        "quantity": a.quantity,
        "unit_price": a.unit_price,
        "net_sales": a.net_sales,
        "anomaly_score": a.anomaly_score,
        "explanation": a.explanation,
        "detected_at": a.detected_at.isoformat() if a.detected_at else None
    } for a in anomalies]


# ==============================================================================
# SIMULATED REST API FOR PAGINATED SALES INGESTION
# ==============================================================================
@router.get("/mock-api/sales")
def mock_sales_api(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=10, le=500)
):
    """
    Simulates a paginated external sales REST endpoint for testing REST ingestion.
    """
    from app.ingestion.generator import SalesDataGenerator
    gen = SalesDataGenerator(seed=42)
    # Generate 500 total sample records across pages
    total_records = 500
    df = gen.generate_records(num_records=total_records, dirty_rate=0.03)

    total_pages = (total_records + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_records)

    page_data = df.iloc[start_idx:end_idx].to_dict(orient="records") if start_idx < total_records else []

    return {
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "total_records": total_records,
        "data": page_data
    }
