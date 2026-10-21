"""
DataPulse AI - Main Dashboard Application (Home)
Multi-page predictive analytics and data engineering monitoring portal.
"""
import sys
from pathlib import Path

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Remove dashboard dir from sys.path if present to avoid any module collisions
dashboard_dir = str(Path(__file__).resolve().parent)
while dashboard_dir in sys.path:
    sys.path.remove(dashboard_dir)

import streamlit as st

# Streamlit Page Config
st.set_page_config(
    page_title="DataPulse AI - Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
css_file = Path(__file__).parent / "styles.css"
if css_file.exists():
    with open(css_file, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Sidebar Branding
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 12px 0 20px 0;">
            <div style="font-size: 1.45rem; font-weight: 800; letter-spacing: -0.02em; color: #38BDF8;">
                ⚡ DataPulse AI
            </div>
            <div style="font-size: 0.8rem; color: #94A3B8; font-weight: 500;">
                Data Engineering & ML Platform
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown(
        """
        **System Architecture**
        - **Bronze:** Raw Storage & Batch Logs
        - **Silver:** Cleaned Staging & Quarantine
        - **Gold:** Star Schema Dimensional Warehouse
        - **ML Engine:** Leak-free Forecasting & Outlier Detection
        - **Orchestration:** Apache Airflow DAG
        - **API:** FastAPI REST & Swagger UI
        """
    )
    st.markdown("---")
    st.info("💡 Use the sidebar navigation above to switch between analytics, ML, and monitoring pages.")

# Main Portal Landing
st.markdown(
    """
    <div style="padding: 30px 0 10px 0;">
        <span class="badge badge-info">Production-Ready Architecture</span>
        <h1 style="font-size: 2.75rem; font-weight: 800; letter-spacing: -0.03em; margin-top: 12px; margin-bottom: 8px;">
            DataPulse AI Platform
        </h1>
        <p style="font-size: 1.15rem; color: #94A3B8; max-width: 850px; line-height: 1.6;">
            An automated end-to-end data platform that ingests raw retail sales transactions,
            enforces schema conformance, quarantines malformed anomalies, structures a Gold Star schema warehouse,
            and serves predictive AI forecasting and isolation forest anomaly detection.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="kpi-card">
            <span class="badge badge-info">Ingestion & ETL</span>
            <h3 style="margin-top: 12px;">Data Pipeline</h3>
            <p style="color: #94A3B8; font-size: 0.9rem;">
                Automated multi-source ingestion from CSV and paginated REST APIs with strict schema validation,
                zero silent data loss, and quarantine tracking.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        """
        <div class="kpi-card">
            <span class="badge badge-success">Analytics Ready</span>
            <h3 style="margin-top: 12px;">Gold Warehouse</h3>
            <p style="color: #94A3B8; font-size: 0.9rem;">
                Normalized Star schema with <code>FactSales</code>, <code>DimProduct</code>,
                <code>DimCustomer</code>, and <code>DimDate</code> enabling sub-second analytical aggregations.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        """
        <div class="kpi-card">
            <span class="badge badge-warning">AI Intelligence</span>
            <h3 style="margin-top: 12px;">Predictive ML</h3>
            <p style="color: #94A3B8; font-size: 0.9rem;">
                7-day sales forecasting with leak-free lag/rolling features and unsupervised
                Isolation Forest outlier detection with transparent explanations.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("### Quick Navigation")
st.write("Navigate directly to any section using the sidebar or the links below:")
n1, n2, n3, n4 = st.columns(4)
with n1:
    if st.button("📊 Executive Overview", use_container_width=True):
        st.switch_page("pages/1_Overview.py")
with n2:
    if st.button("📈 Sales Analytics", use_container_width=True):
        st.switch_page("pages/2_Sales_Analytics.py")
with n3:
    if st.button("🔮 AI Forecasting", use_container_width=True):
        st.switch_page("pages/3_AI_Forecasting.py")
with n4:
    if st.button("🛡️ Data Quality", use_container_width=True):
        st.switch_page("pages/5_Data_Quality.py")
