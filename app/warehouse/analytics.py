"""
DataPulse AI - Warehouse Analytics & Query Engine
Executes production-grade analytical queries for business metrics, trends, KPIs, and data quality health.
"""
from typing import Dict, Any, List, Optional
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text
from app.warehouse.models import (
    FactSales, DimProduct, DimCustomer, DimDate,
    DataQualityIssue, PipelineRun, RawSalesBatch
)


class WarehouseAnalytics:
    """Analytical query engine against the Gold dimensional warehouse and Silver quality tables."""

    @staticmethod
    def get_sales_kpis(db: Session) -> Dict[str, Any]:
        """Calculates executive-level headline KPIs: Total Revenue, Orders, AOV, Units."""
        stats = db.query(
            func.coalesce(func.sum(FactSales.net_sales), 0.0).label("total_revenue"),
            func.count(FactSales.fact_id).label("total_transactions"),
            func.coalesce(func.sum(FactSales.quantity), 0).label("total_units_sold"),
            func.count(func.distinct(FactSales.customer_id)).label("unique_customers"),
            func.count(func.distinct(FactSales.product_id)).label("unique_products")
        ).first()

        total_rev = float(stats.total_revenue) if stats else 0.0
        total_txns = int(stats.total_transactions) if stats else 0
        total_units = int(stats.total_units_sold) if stats else 0
        unique_cust = int(stats.unique_customers) if stats else 0
        unique_prod = int(stats.unique_products) if stats else 0

        aov = round(total_rev / total_txns, 2) if total_txns > 0 else 0.0

        return {
            "total_revenue": round(total_rev, 2),
            "total_transactions": total_txns,
            "average_order_value": aov,
            "total_units_sold": total_units,
            "unique_customers": unique_cust,
            "unique_products": unique_prod
        }

    @staticmethod
    def get_daily_revenue(db: Session, limit_days: int = 90) -> List[Dict[str, Any]]:
        """Retrieves daily aggregated net sales and transaction count ordered chronologically."""
        results = (
            db.query(
                DimDate.full_date.label("sale_date"),
                func.sum(FactSales.net_sales).label("daily_revenue"),
                func.count(FactSales.fact_id).label("transactions_count"),
                func.sum(FactSales.quantity).label("units_sold")
            )
            .join(DimDate, FactSales.date_key == DimDate.date_key)
            .group_by(DimDate.full_date)
            .order_by(DimDate.full_date.asc())
            .all()
        )

        rows = []
        for r in results:
            rows.append({
                "date": str(r.sale_date),
                "revenue": round(float(r.daily_revenue), 2),
                "transactions": int(r.transactions_count),
                "units": int(r.units_sold)
            })
        return rows

    @staticmethod
    def get_monthly_revenue(db: Session) -> List[Dict[str, Any]]:
        """Retrieves monthly revenue and transaction volume."""
        results = (
            db.query(
                DimDate.year,
                DimDate.month,
                DimDate.month_name,
                func.sum(FactSales.net_sales).label("monthly_revenue"),
                func.count(FactSales.fact_id).label("transactions_count")
            )
            .join(DimDate, FactSales.date_key == DimDate.date_key)
            .group_by(DimDate.year, DimDate.month, DimDate.month_name)
            .order_by(DimDate.year.asc(), DimDate.month.asc())
            .all()
        )

        rows = []
        for r in results:
            period_label = f"{r.year}-{int(r.month):02d}"
            rows.append({
                "period": period_label,
                "year": int(r.year),
                "month": int(r.month),
                "month_name": r.month_name,
                "revenue": round(float(r.monthly_revenue), 2),
                "transactions": int(r.transactions_count)
            })
        return rows

    @staticmethod
    def get_revenue_by_category(db: Session) -> List[Dict[str, Any]]:
        """Aggregates revenue and sales share by product category."""
        results = (
            db.query(
                DimProduct.category,
                func.sum(FactSales.net_sales).label("category_revenue"),
                func.count(FactSales.fact_id).label("transactions_count"),
                func.sum(FactSales.quantity).label("units_sold")
            )
            .join(DimProduct, FactSales.product_id == DimProduct.product_id)
            .group_by(DimProduct.category)
            .order_by(desc("category_revenue"))
            .all()
        )

        total_rev = sum(float(r.category_revenue) for r in results) or 1.0
        rows = []
        for r in results:
            rev = round(float(r.category_revenue), 2)
            rows.append({
                "category": r.category,
                "revenue": rev,
                "transactions": int(r.transactions_count),
                "units_sold": int(r.units_sold),
                "share_pct": round((rev / total_rev) * 100, 2)
            })
        return rows

    @staticmethod
    def get_revenue_by_region(db: Session) -> List[Dict[str, Any]]:
        """Aggregates revenue and customer coverage by geographical region."""
        results = (
            db.query(
                DimCustomer.region,
                func.sum(FactSales.net_sales).label("region_revenue"),
                func.count(FactSales.fact_id).label("transactions_count"),
                func.count(func.distinct(FactSales.customer_id)).label("unique_customers")
            )
            .join(DimCustomer, FactSales.customer_id == DimCustomer.customer_id)
            .group_by(DimCustomer.region)
            .order_by(desc("region_revenue"))
            .all()
        )

        total_rev = sum(float(r.region_revenue) for r in results) or 1.0
        rows = []
        for r in results:
            rev = round(float(r.region_revenue), 2)
            rows.append({
                "region": r.region,
                "revenue": rev,
                "transactions": int(r.transactions_count),
                "unique_customers": int(r.unique_customers),
                "share_pct": round((rev / total_rev) * 100, 2)
            })
        return rows

    @staticmethod
    def get_top_products(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns best-selling products by total net revenue and units sold."""
        results = (
            db.query(
                DimProduct.product_id,
                DimProduct.product_name,
                DimProduct.category,
                func.sum(FactSales.net_sales).label("product_revenue"),
                func.sum(FactSales.quantity).label("units_sold"),
                func.count(FactSales.fact_id).label("order_count")
            )
            .join(DimProduct, FactSales.product_id == DimProduct.product_id)
            .group_by(DimProduct.product_id, DimProduct.product_name, DimProduct.category)
            .order_by(desc("product_revenue"))
            .limit(limit)
            .all()
        )

        rows = []
        for r in results:
            rows.append({
                "product_id": r.product_id,
                "product_name": r.product_name,
                "category": r.category,
                "revenue": round(float(r.product_revenue), 2),
                "units_sold": int(r.units_sold),
                "orders": int(r.order_count)
            })
        return rows

    @staticmethod
    def get_sales_growth(db: Session) -> List[Dict[str, Any]]:
        """Computes Month-over-Month (MoM) revenue growth velocity."""
        monthly = WarehouseAnalytics.get_monthly_revenue(db)
        if not monthly:
            return []

        rows_with_growth = []
        prev_rev = None

        for item in monthly:
            current_rev = item["revenue"]
            growth_pct = None
            if prev_rev is not None and prev_rev > 0:
                growth_pct = round(((current_rev - prev_rev) / prev_rev) * 100, 2)
            
            item_copy = dict(item)
            item_copy["growth_pct"] = growth_pct
            rows_with_growth.append(item_copy)
            prev_rev = current_rev

        return rows_with_growth

    @staticmethod
    def get_data_quality_metrics(db: Session) -> Dict[str, Any]:
        """Audits quarantine repository and pipeline runs to summarize data quality."""
        total_quarantined = db.query(func.count(DataQualityIssue.issue_id)).scalar() or 0
        total_valid = db.query(func.count(FactSales.fact_id)).scalar() or 0
        total_batches = db.query(func.count(RawSalesBatch.batch_id)).scalar() or 0

        # Breakdown by violated rule
        violations = (
            db.query(
                DataQualityIssue.rule_violated,
                func.count(DataQualityIssue.issue_id).label("count")
            )
            .group_by(DataQualityIssue.rule_violated)
            .order_by(desc("count"))
            .all()
        )

        violations_dict = {v.rule_violated: int(v.count) for v in violations}

        total_ingested = total_valid + total_quarantined
        rejection_rate = (
            round((total_quarantined / total_ingested) * 100, 2) if total_ingested > 0 else 0.0
        )

        return {
            "total_batches_processed": total_batches,
            "total_records_ingested": total_ingested,
            "valid_records_stored": total_valid,
            "quarantined_records": total_quarantined,
            "overall_rejection_rate_pct": rejection_rate,
            "violations_breakdown": violations_dict
        }

    @staticmethod
    def get_recent_transactions(
        db: Session,
        limit: int = 100,
        region: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Queries granular validated transactions joined across Star schema dimensions."""
        query = (
            db.query(
                FactSales.transaction_id,
                DimDate.full_date.label("transaction_date"),
                DimProduct.product_id,
                DimProduct.product_name,
                DimProduct.category,
                FactSales.quantity,
                FactSales.unit_price,
                FactSales.discount,
                FactSales.net_sales,
                DimCustomer.region,
                DimCustomer.customer_id,
                FactSales.batch_id
            )
            .join(DimDate, FactSales.date_key == DimDate.date_key)
            .join(DimProduct, FactSales.product_id == DimProduct.product_id)
            .join(DimCustomer, FactSales.customer_id == DimCustomer.customer_id)
        )

        if region and region != "All":
            query = query.filter(DimCustomer.region == region)
        if category and category != "All":
            query = query.filter(DimProduct.category == category)

        results = query.order_by(DimDate.full_date.desc(), FactSales.fact_id.desc()).limit(limit).all()

        rows = []
        for r in results:
            rows.append({
                "transaction_id": r.transaction_id,
                "transaction_date": str(r.transaction_date),
                "product_id": r.product_id,
                "product_name": r.product_name,
                "category": r.category,
                "quantity": r.quantity,
                "unit_price": r.unit_price,
                "discount": r.discount,
                "net_sales": r.net_sales,
                "region": r.region,
                "customer_id": r.customer_id,
                "batch_id": r.batch_id
            })
        return rows
