"""
DataPulse AI - Sales Analytics Page
In-depth dimensional analysis: Category performance, Regional distribution, Top products, and MoM growth.
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
from dashboard.components.charts import (
    plot_revenue_trend, plot_category_distribution, plot_regional_comparison
)
from dashboard.components.data_client import DashboardDataClient

client = DashboardDataClient()

render_header(
    title="Sales & Revenue Analytics",
    subtitle="Deep dimensional insights across product lines, geographical markets, and growth trajectories.",
    badge="Gold Warehouse"
)

# Fetch Data
cat_data = client.get_category_sales()
reg_data = client.get_region_sales()
top_prods = client.get_top_products(limit=10)
growth_data = client.get_sales_growth()

# Row 1: Category and Region Breakdowns
c1, c2 = st.columns(2)

with c1:
    if cat_data:
        df_cat = pd.DataFrame(cat_data)
        fig_cat = plot_category_distribution(df_cat)
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("No category data available.")

with c2:
    if reg_data:
        df_reg = pd.DataFrame(reg_data)
        fig_reg = plot_regional_comparison(df_reg)
        st.plotly_chart(fig_reg, use_container_width=True)
    else:
        st.info("No regional data available.")

st.markdown("---")

# Row 2: Top Selling Products
st.markdown("### Top 10 Best-Selling Products")
if top_prods:
    df_prods = pd.DataFrame(top_prods)
    # Format currency for display
    df_prods_display = df_prods.copy()
    df_prods_display["revenue"] = df_prods_display["revenue"].apply(lambda v: f"${v:,.2f}")
    df_prods_display["units_sold"] = df_prods_display["units_sold"].apply(lambda v: f"{v:,}")
    df_prods_display["orders"] = df_prods_display["orders"].apply(lambda v: f"{v:,}")
    df_prods_display.columns = ["Product ID", "Product Name", "Category", "Net Revenue", "Units Sold", "Order Count"]
    st.dataframe(df_prods_display, use_container_width=True, hide_index=True)
else:
    st.info("No product ranking data available.")

st.markdown("---")

# Row 3: Month-over-Month Growth Velocity
st.markdown("### Month-over-Month (MoM) Revenue Growth")
if growth_data:
    df_growth = pd.DataFrame(growth_data)
    cols = st.columns(len(df_growth))
    for idx, row in df_growth.iterrows():
        with cols[idx]:
            growth_val = row.get("growth_pct")
            growth_str = f"{growth_val:+.1f}%" if growth_val is not None else "Baseline"
            badge_type = "success" if (growth_val and growth_val > 0) else ("danger" if (growth_val and growth_val < 0) else "info")
            render_kpi_card(
                title=f"{row['month_name']} {row['year']}",
                value=f"${row['revenue']:,.0f}",
                subtitle=f"{row['transactions']:,} transactions",
                badge_text=growth_str,
                badge_type=badge_type
            )
else:
    st.info("No monthly growth metrics available yet.")
