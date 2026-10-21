"""
DataPulse AI - Data Quality Reporting Engine
Compiles comprehensive quality health audits, metric breakdowns, and quarantine summaries.
"""
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
from app.transformations.validator import ValidationResult


class DataQualityReporter:
    """Generates auditable, production-grade data quality scorecards for each ingestion batch."""

    def __init__(self, batch_id: str):
        self.batch_id = batch_id

    def build_quality_report(
        self,
        validation_result: ValidationResult,
        transformed_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive Data Quality scorecard covering completeness,
        uniqueness, validity, and statistical boundaries.
        """
        # Aggregate breakdown of failure reasons
        issues_breakdown: Dict[str, int] = {}
        for rec in validation_result.quarantine_records:
            rule = rec.get("rule_violated", "UNKNOWN")
            issues_breakdown[rule] = issues_breakdown.get(rule, 0) + 1

        # Calculate numeric statistics on transformed clean data
        stats = {}
        if not transformed_df.empty:
            stats = {
                "total_net_sales": round(float(transformed_df["net_sales"].sum()), 2),
                "avg_net_sales": round(float(transformed_df["net_sales"].mean()), 2),
                "min_net_sales": round(float(transformed_df["net_sales"].min()), 2),
                "max_net_sales": round(float(transformed_df["net_sales"].max()), 2),
                "total_units_sold": int(transformed_df["quantity"].sum()),
                "unique_products": int(transformed_df["product_id"].nunique()),
                "unique_customers": int(transformed_df["customer_id"].nunique()),
                "unique_regions": int(transformed_df["region"].nunique()),
            }

        # Quality health verdict
        rejection_rate = validation_result.rejection_rate
        if rejection_rate == 0.0:
            health_verdict = "EXCELLENT"
        elif rejection_rate < 0.05:
            health_verdict = "HEALTHY"
        elif rejection_rate < 0.20:
            health_verdict = "ACCEPTABLE_WITH_QUARANTINE"
        else:
            health_verdict = "CRITICAL_HIGH_FAILURE_RATE"

        report = {
            "batch_id": self.batch_id,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "records_received": validation_result.total_input,
                "records_accepted": validation_result.accepted_count,
                "records_quarantined": validation_result.rejected_count,
                "duplicates_detected": validation_result.duplicate_count,
                "rejection_rate_pct": round(rejection_rate * 100, 2),
                "health_verdict": health_verdict
            },
            "rule_violations_breakdown": issues_breakdown,
            "business_metrics": stats
        }
        return report
