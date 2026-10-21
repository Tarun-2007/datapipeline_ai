"""
DataPulse AI - Data Explorer Page
Filterable query table of validated Gold warehouse transactions with live CSV export capabilities.
"""
import sys
from pathlib import Path

# Ensure project root is prioritized in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd

from dashboard.components.metrics_cards import render_header
from dashboard.components.data_client import DashboardDataClient

client = DashboardDataClient()

render_header(
    title="Data Warehouse Explorer",
    subtitle="Interactive search and granular inspection of clean Gold FactSales records with CSV export.",
    badge="Gold FactSales"
)

# Filters Bar
f1, f2, f3 = st.columns([1.5, 1.5, 1])

with f1:
    region_choice = st.selectbox(
        "Filter by Region",
        ["All", "North", "South", "East", "West", "Central"],
        index=0
    )

with f2:
    cat_choice = st.selectbox(
        "Filter by Category",
        ["All", "Electronics", "Home & Office", "Home & Kitchen", "Apparel", "Sports & Outdoors", "Books"],
        index=0
    )

with f3:
    limit_choice = st.selectbox("Max Records", [100, 250, 500, 1000], index=0)

# Fetch Records
transactions = client.get_transactions(
    limit=limit_choice,
    region=region_choice,
    category=cat_choice
)

st.markdown("---")

if transactions:
    df_txns = pd.DataFrame(transactions)
    
    # Summary info bar
    c_info, c_export = st.columns([3, 1])
    with c_info:
        st.write(f"Showing **{len(df_txns):,}** validated transactions.")
    with c_export:
        csv_bytes = df_txns.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export as CSV",
            data=csv_bytes,
            file_name="datapulse_sales_export.csv",
            mime="text/csv",
            use_container_width=True
        )

    # Clean display columns
    display_df = df_txns.copy()
    display_df["unit_price"] = display_df["unit_price"].apply(lambda v: f"${v:,.2f}")
    display_df["discount"] = display_df["discount"].apply(lambda v: f"{v*100:.1f}%")
    display_df["net_sales"] = display_df["net_sales"].apply(lambda v: f"${v:,.2f}")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("No records found matching current criteria. Ingest data via the Overview or Pipeline Monitoring page.")
