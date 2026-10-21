"""
DataPulse AI - Anomaly Detection Page
Isolation Forest unsupervised outlier scoring, multidimensional feature space, and transparent explanations.
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
from dashboard.components.charts import plot_anomalies_scatter
from dashboard.components.data_client import DashboardDataClient

client = DashboardDataClient()

render_header(
    title="Sales Anomaly Detection",
    subtitle="Unsupervised outlier identification via Isolation Forest with automated diagnostic reasoning.",
    badge="IsolationForest"
)

# Filters Bar
col_f1, col_f2, col_act = st.columns([1.5, 1.5, 2])
with col_f1:
    region_filter = st.selectbox("Filter Region", ["All", "North", "South", "East", "West", "Central"], index=0)
with col_f2:
    cat_filter = st.selectbox("Filter Category", ["All", "Electronics", "Home & Office", "Home & Kitchen", "Apparel", "Sports & Outdoors", "Books"], index=0)
with col_act:
    st.write("")
    if st.button("🔍 Run Anomaly Detection Scan", use_container_width=True):
        with st.spinner("Scoring recent transactions with Isolation Forest..."):
            from app.core.database import SessionLocal
            from app.warehouse.analytics import WarehouseAnalytics
            from app.ml.anomaly import SalesAnomalyDetector
            from app.warehouse.models import SalesAnomaly
            db = SessionLocal()
            try:
                txns = WarehouseAnalytics.get_recent_transactions(db, limit=3000)
                if len(txns) >= 50:
                    df_txns = pd.DataFrame(txns)
                    detector = SalesAnomalyDetector()
                    detector.train(df_txns)
                    scored = detector.detect_anomalies(df_txns)

                    db.query(SalesAnomaly).delete()
                    for _, row in scored[scored["is_anomaly"]].iterrows():
                        anom = SalesAnomaly(
                            transaction_id=str(row["transaction_id"]),
                            transaction_date=pd.to_datetime(row["transaction_date"]).date(),
                            product_id=str(row["product_id"]),
                            category=str(row["category"]),
                            region=str(row["region"]),
                            quantity=int(row["quantity"]),
                            unit_price=float(row["unit_price"]),
                            net_sales=float(row["net_sales"]),
                            anomaly_score=float(row["anomaly_score"]),
                            is_anomaly=True,
                            explanation=str(row["explanation"])
                        )
                        db.add(anom)
                    db.commit()
                    st.success("Anomaly detection scan complete!")
                    st.rerun()
                else:
                    st.warning("Need at least 50 historical transactions to train anomaly detector.")
            finally:
                db.close()

st.markdown("---")

# Fetch Anomalies
anomalies = client.get_anomalies(limit=200, region=region_filter, category=cat_filter)
txns_sample = client.get_transactions(limit=300, region=region_filter, category=cat_filter)

# KPI Summary
a1, a2, a3 = st.columns(3)
with a1:
    render_kpi_card(
        title="Flagged Anomalies",
        value=f"{len(anomalies):,}",
        subtitle="Current filter selection",
        badge_text="Outliers",
        badge_type="danger"
    )
with a2:
    max_score = max([a["anomaly_score"] for a in anomalies]) if anomalies else 0.0
    render_kpi_card(
        title="Peak Anomaly Score",
        value=f"{max_score:.3f}",
        subtitle="Higher = greater deviation",
        badge_text="Magnitude",
        badge_type="warning"
    )
with a3:
    render_kpi_card(
        title="Algorithm Model",
        value="Isolation Forest",
        subtitle="Contamination = 3.0%",
        badge_text="Unsupervised",
        badge_type="info"
    )

# Scatter Plot
if txns_sample:
    df_plot = pd.DataFrame(txns_sample)
    # Tag anomalies in sample
    anom_ids = {a["transaction_id"] for a in anomalies}
    df_plot["is_anomaly"] = df_plot["transaction_id"].isin(anom_ids)
    fig_scatter = plot_anomalies_scatter(df_plot)
    st.plotly_chart(fig_scatter, use_container_width=True)

# Granular Anomalies Table with Explanations
st.markdown("### Flagged Outlier Transactions & Explanations")
if anomalies:
    df_anom = pd.DataFrame(anomalies)[[
        "transaction_id", "transaction_date", "product_id", "category", "region",
        "quantity", "unit_price", "net_sales", "anomaly_score", "explanation"
    ]]
    st.dataframe(df_anom, use_container_width=True, hide_index=True)
else:
    st.info("No anomalies found matching current filters. Run an anomaly detection scan above.")
