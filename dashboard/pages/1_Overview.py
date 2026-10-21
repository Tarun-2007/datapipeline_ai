"""
DataPulse AI - Overview Page
Executive headline metrics, daily revenue trajectory, and latest pipeline execution summary.
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
from dashboard.components.charts import plot_revenue_trend
from dashboard.components.data_client import DashboardDataClient

client = DashboardDataClient()

render_header(
    title="Executive Overview",
    subtitle="High-level operational health, pipeline execution status, and core financial performance.",
    badge="Live Warehouse"
)

# Fetch Data
kpis = client.get_kpis()
daily_data = client.get_daily_revenue()
runs = client.get_pipeline_history(limit=5)

# Row 1: KPI Cards
c1, c2, c3, c4 = st.columns(4)

with c1:
    rev = kpis.get("total_revenue", 0.0)
    render_kpi_card(
        title="Total Net Revenue",
        value=f"${rev:,.2f}",
        subtitle="Gross revenue net of discounts",
        badge_text="Gold Tier",
        badge_type="success"
    )

with c2:
    txns = kpis.get("total_transactions", 0)
    render_kpi_card(
        title="Total Transactions",
        value=f"{txns:,}",
        subtitle="Validated sales records stored",
        badge_text="Verified",
        badge_type="info"
    )

with c3:
    aov = kpis.get("average_order_value", 0.0)
    render_kpi_card(
        title="Average Order Value",
        value=f"${aov:,.2f}",
        subtitle="Per valid checkout transaction",
        badge_text="AOV",
        badge_type="warning"
    )

with c4:
    latest_run = runs[0] if runs else {}
    status = latest_run.get("status", "IDLE")
    badge_type = "success" if status == "SUCCESS" else ("warning" if status == "RUNNING" else "info")
    render_kpi_card(
        title="Latest Pipeline Status",
        value=status,
        subtitle=f"Run: {latest_run.get('run_id', 'None')[:16]}",
        badge_text="Pipeline",
        badge_type=badge_type
    )

st.markdown("---")

# Row 2: Sales Trajectory & Quick Pipeline Action
col_chart, col_side = st.columns([2.5, 1])

with col_chart:
    if daily_data:
        df_daily = pd.DataFrame(daily_data)
        fig = plot_revenue_trend(df_daily)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No daily sales data available yet. Run the pipeline below to ingest records.")

with col_side:
    st.markdown("### Quick Pipeline Trigger")
    st.write("Trigger an automated ingestion batch directly from the dashboard:")
    source_choice = st.selectbox("Ingestion Source", ["csv", "simulated_api"], index=0)
    
    if st.button("🚀 Trigger Ingestion Run", use_container_width=True):
        with st.spinner(f"Ingesting via {source_choice}..."):
            try:
                from app.ingestion.pipeline import SalesDataPipeline
                with SalesDataPipeline() as pipeline:
                    res = pipeline.run_pipeline(source_type=source_choice)
                    st.success(f"Batch {res['run_summary']['batch_id']} completed successfully!")
                    st.rerun()
            except Exception as e:
                st.error(f"Pipeline run failed: {e}")

    st.markdown("---")
    st.markdown("### Dimension Coverage")
    st.write(f"👥 **Unique Customers:** {kpis.get('unique_customers', 0):,}")
    st.write(f"📦 **Unique Products:** {kpis.get('unique_products', 0):,}")
    st.write(f"🛒 **Total Units Sold:** {kpis.get('total_units_sold', 0):,}")

# Row 3: Recent Pipeline Executions Table
st.markdown("### Recent Pipeline Executions")
if runs:
    df_runs = pd.DataFrame(runs)[[
        "run_id", "batch_id", "source", "start_time", "duration_seconds",
        "records_ingested", "records_processed", "records_quarantined", "status"
    ]]
    st.dataframe(df_runs, use_container_width=True, hide_index=True)
else:
    st.write("No pipeline execution runs recorded yet.")
