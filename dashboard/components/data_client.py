"""
DataPulse AI - Resilient Dashboard Data Client
Fetches data from FastAPI backend with automatic zero-latency fallback to direct database access.
"""
import sys
from pathlib import Path

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, Any, List, Optional
import requests
import pandas as pd

from app.core.config import settings
from app.core.database import SessionLocal
from app.warehouse.analytics import WarehouseAnalytics
from app.monitoring.metrics import PlatformMonitor


class DashboardDataClient:
    """Provides high-availability data access for Streamlit."""

    def __init__(self, api_base_url: str = None):
        self.api_base_url = api_base_url or f"http://{settings.API_HOST}:{settings.API_PORT}{settings.API_V1_PREFIX}"

    def _api_get(self, endpoint: str, params: dict = None) -> Optional[Any]:
        """Attempts to fetch from FastAPI REST endpoint."""
        try:
            resp = requests.get(f"{self.api_base_url}{endpoint}", params=params, timeout=2.0)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def get_kpis(self) -> Dict[str, Any]:
        """Fetches sales headline KPIs."""
        data = self._api_get("/sales/summary")
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_sales_kpis(db)
        finally:
            db.close()

    def get_daily_revenue(self) -> List[Dict[str, Any]]:
        """Fetches daily revenue trajectory."""
        data = self._api_get("/sales/trends")
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_daily_revenue(db)
        finally:
            db.close()

    def get_monthly_revenue(self) -> List[Dict[str, Any]]:
        """Fetches monthly revenue."""
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_monthly_revenue(db)
        finally:
            db.close()

    def get_category_sales(self) -> List[Dict[str, Any]]:
        """Fetches sales by category."""
        data = self._api_get("/sales/by-category")
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_revenue_by_category(db)
        finally:
            db.close()

    def get_region_sales(self) -> List[Dict[str, Any]]:
        """Fetches sales by region."""
        data = self._api_get("/sales/by-region")
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_revenue_by_region(db)
        finally:
            db.close()

    def get_top_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetches top-selling products."""
        data = self._api_get("/sales/top-products", params={"limit": limit})
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_top_products(db, limit=limit)
        finally:
            db.close()

    def get_sales_growth(self) -> List[Dict[str, Any]]:
        """Fetches MoM sales growth."""
        data = self._api_get("/sales/growth")
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_sales_growth(db)
        finally:
            db.close()

    def get_quality_summary(self) -> Dict[str, Any]:
        """Fetches data quality metrics."""
        data = self._api_get("/data-quality/summary")
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_data_quality_metrics(db)
        finally:
            db.close()

    def get_quarantine_issues(self, limit: int = 100, rule: str = None) -> List[Dict[str, Any]]:
        """Fetches quarantined records."""
        params = {"limit": limit}
        if rule:
            params["rule"] = rule
        data = self._api_get("/data-quality/issues", params=params)
        if data is not None:
            return data
        from app.warehouse.models import DataQualityIssue
        db = SessionLocal()
        try:
            q = db.query(DataQualityIssue)
            if rule:
                q = q.filter(DataQualityIssue.rule_violated == rule)
            issues = q.order_by(DataQualityIssue.issue_id.desc()).limit(limit).all()
            return [{
                "issue_id": i.issue_id,
                "batch_id": i.batch_id,
                "transaction_id": i.transaction_id,
                "rule_violated": i.rule_violated,
                "rejected_value": i.rejected_value,
                "rejection_reason": i.rejection_reason,
                "raw_payload": i.raw_payload,
                "quarantined_at": i.quarantined_at.strftime("%Y-%m-%d %H:%M:%S") if i.quarantined_at else None
            } for i in issues]
        finally:
            db.close()

    def get_pipeline_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches pipeline run history."""
        data = self._api_get("/pipeline/runs", params={"limit": limit})
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return PlatformMonitor.get_pipeline_runs_history(db, limit=limit)
        finally:
            db.close()

    def get_sla_metrics(self) -> Dict[str, Any]:
        """Fetches SLA summary metrics."""
        db = SessionLocal()
        try:
            return PlatformMonitor.get_pipeline_sla_summary(db)
        finally:
            db.close()

    def get_forecasts(self) -> Dict[str, Any]:
        """Fetches AI sales forecasts."""
        data = self._api_get("/forecasts")
        if data is not None:
            return data
        from app.warehouse.models import SalesForecast
        db = SessionLocal()
        try:
            fcs = db.query(SalesForecast).order_by(SalesForecast.forecast_date.asc()).all()
            if not fcs:
                return {"forecasts": [], "metrics": {}}
            return {
                "forecasts": [{
                    "forecast_date": str(f.forecast_date),
                    "predicted_sales": f.predicted_sales,
                    "lower_bound": f.lower_bound,
                    "upper_bound": f.upper_bound,
                    "model_type": f.model_type
                } for f in fcs],
                "metrics": {"mae": fcs[0].mae, "rmse": fcs[0].rmse, "model_type": fcs[0].model_type}
            }
        finally:
            db.close()

    def get_anomalies(self, limit: int = 100, region: str = None, category: str = None) -> List[Dict[str, Any]]:
        """Fetches flagged sales anomalies."""
        data = self._api_get("/anomalies", params={"limit": limit, "region": region, "category": category})
        if data is not None:
            return data
        from app.warehouse.models import SalesAnomaly
        db = SessionLocal()
        try:
            q = db.query(SalesAnomaly).filter(SalesAnomaly.is_anomaly == True)
            if region and region != "All":
                q = q.filter(SalesAnomaly.region == region)
            if category and category != "All":
                q = q.filter(SalesAnomaly.category == category)
            anoms = q.order_by(SalesAnomaly.anomaly_score.desc()).limit(limit).all()
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
                "detected_at": a.detected_at.strftime("%Y-%m-%d %H:%M:%S") if a.detected_at else None
            } for a in anoms]
        finally:
            db.close()

    def get_transactions(self, limit: int = 100, region: str = None, category: str = None) -> List[Dict[str, Any]]:
        """Fetches granular transactions for data explorer."""
        data = self._api_get("/sales/transactions", params={"limit": limit, "region": region, "category": category})
        if data is not None:
            return data
        db = SessionLocal()
        try:
            return WarehouseAnalytics.get_recent_transactions(db, limit=limit, region=region, category=category)
        finally:
            db.close()
