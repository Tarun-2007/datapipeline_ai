"""
DataPulse AI - AI Forecasting Page
Interactive 7-day multi-step sales predictions, baseline comparison benchmarks, and model evaluation metrics.
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
from dashboard.components.charts import plot_forecast_with_intervals
from dashboard.components.data_client import DashboardDataClient

client = DashboardDataClient()

render_header(
    title="AI Sales Forecasting",
    subtitle="Predictive 7-day multi-step sales demand forecasting using leak-free lag and rolling features.",
    badge="RandomForestRegressor"
)

# Callout Disclaimer
st.markdown(
    """
    <div class="info-callout">
        ⚠️ <b>Demonstration Note:</b> Predictions are generated from algorithmic machine learning models
        (Random Forest Regressor vs Seasonal 7-Day Baseline) trained on synthetic sales transactions.
    </div>
    """,
    unsafe_allow_html=True
)

# Fetch Data
fc_payload = client.get_forecasts()
daily_data = client.get_daily_revenue()

forecasts = fc_payload.get("forecasts", [])
metrics = fc_payload.get("metrics", {})

# Action bar to retrain model
c_train, c_info = st.columns([1, 3])
with c_train:
    if st.button("🔄 Retrain Forecasting Model", use_container_width=True):
        with st.spinner("Engineering features and retraining model..."):
            if len(daily_data) >= 20:
                from app.ml.forecasting import SalesForecaster
                forecaster = SalesForecaster()
                forecaster.train_and_evaluate(pd.DataFrame(daily_data))
                preds = forecaster.predict_next_7_days(pd.DataFrame(daily_data))
                # Persist
                from app.core.database import SessionLocal
                from app.warehouse.models import SalesForecast
                db = SessionLocal()
                try:
                    db.query(SalesForecast).delete()
                    for p in preds:
                        sf = SalesForecast(
                            forecast_date=pd.to_datetime(p["forecast_date"]).date(),
                            predicted_sales=p["predicted_sales"],
                            lower_bound=p["lower_bound"],
                            upper_bound=p["upper_bound"],
                            model_type=p["model_type"],
                            mae=forecaster.metrics.get("ml_model", {}).get("mae"),
                            rmse=forecaster.metrics.get("ml_model", {}).get("rmse")
                        )
                        db.add(sf)
                    db.commit()
                finally:
                    db.close()
                st.success("Model retrained and forecasts updated!")
                st.rerun()
            else:
                st.warning("Insufficient daily sales data (need >= 20 days). Run the pipeline first.")

with c_info:
    st.write(f"Model Architecture: **Random Forest (100 estimators, max_depth=6)** | Validation Split: **Strict chronological out-of-sample**")

st.markdown("---")

# Row 1: Model Benchmark Scorecards
b1, b2, b3, b4 = st.columns(4)

with b1:
    mae = metrics.get("mae", 0.0)
    render_kpi_card(
        title="ML Test MAE",
        value=f"${mae:,.2f}" if mae else "N/A",
        subtitle="Mean Absolute Error",
        badge_text="Test Metric",
        badge_type="info"
    )

with b2:
    rmse = metrics.get("rmse", 0.0)
    render_kpi_card(
        title="ML Test RMSE",
        value=f"${rmse:,.2f}" if rmse else "N/A",
        subtitle="Root Mean Squared Error",
        badge_text="Test Metric",
        badge_type="info"
    )

with b3:
    render_kpi_card(
        title="Forecast Horizon",
        value="7 Days",
        subtitle="Recursive multi-step forward",
        badge_text="Daily Grain",
        badge_type="success"
    )

with b4:
    total_proj = sum(f["predicted_sales"] for f in forecasts) if forecasts else 0.0
    render_kpi_card(
        title="Projected 7-Day Net",
        value=f"${total_proj:,.2f}",
        subtitle="Cumulative expected sales",
        badge_text="Projected",
        badge_type="warning"
    )

# Row 2: Interactive Forecast Plot
if daily_data and forecasts:
    fig_fc = plot_forecast_with_intervals(pd.DataFrame(daily_data), forecasts)
    st.plotly_chart(fig_fc, use_container_width=True)
else:
    st.info("Run the ingestion pipeline and retrain the model to populate forecast predictions.")

# Row 3: Forecast Table
st.markdown("### Projected Daily Forecast Schedule")
if forecasts:
    df_fc = pd.DataFrame(forecasts)
    df_fc_display = df_fc.copy()
    df_fc_display["predicted_sales"] = df_fc_display["predicted_sales"].apply(lambda v: f"${v:,.2f}")
    df_fc_display["lower_bound"] = df_fc_display["lower_bound"].apply(lambda v: f"${v:,.2f}")
    df_fc_display["upper_bound"] = df_fc_display["upper_bound"].apply(lambda v: f"${v:,.2f}")
    df_fc_display.columns = ["Target Date", "Predicted Revenue", "Lower Bound (95%)", "Upper Bound (95%)", "Algorithm"]
    st.dataframe(df_fc_display, use_container_width=True, hide_index=True)
