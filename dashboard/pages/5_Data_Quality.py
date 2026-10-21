"""
DataPulse AI - Data Quality & Quarantine Audit Page
Evaluates schema integrity, rejection rate thresholds, violation rule breakdowns, and quarantined records.
"""
import sys
from pathlib import Path

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from dashboard.components.metrics_cards import render_header, render_kpi_card
from dashboard.components.charts import plot_quality_violations
from dashboard.components.data_client import DashboardDataClient

client = DashboardDataClient()

render_header(
    title="Data Quality & Quarantine Auditing",
    subtitle="Continuous validation scorecard, rule conformance metrics, and forensic quarantine inspection.",
    badge="Zero Silent Loss"
)

# Fetch Data
dq_metrics = client.get_quality_summary()
violations = dq_metrics.get("violations_breakdown", {})
issues = client.get_quarantine_issues(limit=150)

# Row 1: Quality Scorecard KPIs
q1, q2, q3, q4 = st.columns(4)

with q1:
    total_ingested = dq_metrics.get("total_records_ingested", 0)
    render_kpi_card(
        title="Total Ingested Records",
        value=f"{total_ingested:,}",
        subtitle="Across all batch sources",
        badge_text="Volume",
        badge_type="info"
    )

with q2:
    valid_stored = dq_metrics.get("valid_records_stored", 0)
    render_kpi_card(
        title="Valid Records Stored",
        value=f"{valid_stored:,}",
        subtitle="Loaded to Gold warehouse",
        badge_text="Accepted",
        badge_type="success"
    )

with q3:
    quarantined = dq_metrics.get("quarantined_records", 0)
    render_kpi_card(
        title="Quarantined Records",
        value=f"{quarantined:,}",
        subtitle="Zero silent record drops",
        badge_text="Quarantined",
        badge_type="warning"
    )

with q4:
    rej_rate = dq_metrics.get("overall_rejection_rate_pct", 0.0)
    status_type = "success" if rej_rate < 5.0 else ("warning" if rej_rate < 20.0 else "danger")
    render_kpi_card(
        title="Rejection Rate",
        value=f"{rej_rate:.2f}%",
        subtitle="Threshold target: < 20%",
        badge_text="SLA Check",
        badge_type=status_type
    )

st.markdown("---")

# Row 2: Violations Chart & Quality Architecture Explanation
col_chart, col_rules = st.columns([1.8, 1.2])

with col_chart:
    if violations:
        fig_viol = plot_quality_violations(violations)
        st.plotly_chart(fig_viol, use_container_width=True)
    else:
        st.info("No data quality violations registered yet.")

with col_rules:
    st.markdown("### Active Validation Rules")
    st.markdown(
        """
        - **`MISSING_TRANSACTION_ID`**: Rejects null or blank primary key.
        - **`DUPLICATE_TRANSACTION_ID`**: Deduplicates on business key.
        - **`MISSING_CUSTOMER_ID`**: Enforces dimensional integrity.
        - **`MISSING_PRODUCT_ID`**: Enforces catalog relationship.
        - **`INVALID_DATE_FORMAT`**: Catches unparsable date values.
        - **`NON_POSITIVE_QUANTITY`**: Rejects quantities `<= 0`.
        - **`NON_POSITIVE_PRICE`**: Catches unit price `<= 0.0`.
        - **`INVALID_DISCOUNT_RANGE`**: Enforces `0.0 <= discount < 1.0`.
        """
    )

st.markdown("---")

# Row 3: Forensic Quarantine Table
st.markdown("### Quarantined Record Repository")
st.write("Inspect quarantined records, violated rules, and original raw payloads:")

rule_filter = st.selectbox(
    "Filter by Rule Violated",
    ["All"] + list(violations.keys()) if violations else ["All"]
)

filtered_issues = issues
if rule_filter != "All":
    filtered_issues = [i for i in issues if i["rule_violated"] == rule_filter]

if filtered_issues:
    df_issues = pd.DataFrame(filtered_issues)[[
        "issue_id", "batch_id", "transaction_id", "rule_violated",
        "rejected_value", "rejection_reason", "quarantined_at"
    ]]
    st.dataframe(df_issues, use_container_width=True, hide_index=True)
else:
    st.info("No quarantined records match the selected filter.")
