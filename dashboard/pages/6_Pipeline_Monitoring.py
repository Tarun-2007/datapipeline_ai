"""
DataPulse AI - Pipeline Monitoring Page
Pipeline execution history, batch duration trends, SLA uptime, and operational run logs.
"""
import sys
from pathlib import Path

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard.components.metrics_cards import render_header, render_kpi_card
from dashboard.components.charts import DARK_LAYOUT
from dashboard.components.data_client import DashboardDataClient

client = DashboardDataClient()

render_header(
    title="Pipeline Monitoring & SLA Health",
    subtitle="Execution telemetry, batch processing latencies, throughput tracking, and system reliability.",
    badge="SLA Audited"
)

# Fetch Data
sla = client.get_sla_metrics()
history = client.get_pipeline_history(limit=50)

# Row 1: SLA KPI Scorecards
s1, s2, s3, s4 = st.columns(4)

with s1:
    rate = sla.get("success_rate_pct", 100.0)
    b_type = "success" if rate >= 95.0 else ("warning" if rate >= 80.0 else "danger")
    render_kpi_card(
        title="Pipeline Success Rate",
        value=f"{rate:.1f}%",
        subtitle=f"{sla.get('successful_runs', 0)} / {sla.get('total_runs', 0)} runs",
        badge_text="SLA Target 99%",
        badge_type=b_type
    )

with s2:
    avg_sec = sla.get("avg_duration_seconds", 0.0)
    render_kpi_card(
        title="Average Batch Latency",
        value=f"{avg_sec:.2f}s",
        subtitle="End-to-end processing time",
        badge_text="Latency",
        badge_type="info"
    )

with s3:
    failed = sla.get("failed_runs", 0)
    render_kpi_card(
        title="Failed Runs",
        value=f"{failed}",
        subtitle="Captured with error traceback",
        badge_text="Faults",
        badge_type="danger" if failed > 0 else "success"
    )

with s4:
    total_runs = sla.get("total_runs", 0)
    render_kpi_card(
        title="Total Audited Runs",
        value=f"{total_runs}",
        subtitle="Persisted in pipeline_runs",
        badge_text="Audit Trail",
        badge_type="info"
    )

st.markdown("---")

# Row 2: Latency Duration Chart
if history:
    df_hist = pd.DataFrame(history)
    fig_dur = px.bar(
        df_hist,
        x="run_id",
        y="duration_seconds",
        color="status",
        color_discrete_map={"SUCCESS": "#10B981", "FAILED": "#F43F5E", "RUNNING": "#F59E0B"},
        labels={"duration_seconds": "Duration (seconds)", "run_id": "Pipeline Run ID"}
    )
    fig_dur.update_layout(title="<b>Batch Execution Latency Duration (s)</b>", **DARK_LAYOUT)
    st.plotly_chart(fig_dur, use_container_width=True)

# Row 3: Pipeline Audit Trail Table
st.markdown("### Execution Audit History")
if history:
    df_runs_table = pd.DataFrame(history)[[
        "run_id", "batch_id", "source", "start_time", "end_time",
        "duration_seconds", "records_ingested", "records_processed",
        "records_quarantined", "status", "error_details"
    ]]
    st.dataframe(df_runs_table, use_container_width=True, hide_index=True)
else:
    st.info("No pipeline run records available yet.")
