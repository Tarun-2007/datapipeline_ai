"""
DataPulse AI - Plotly Visualization Engine
Generates interactive, responsive charts styled for dark glassmorphism analytics.
"""
from typing import Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(17, 24, 39, 0.4)",
    font=dict(family="Inter, sans-serif", color="#E2E8F0"),
    margin=dict(l=40, r=20, t=40, b=40),
    xaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)", zerolinecolor="rgba(255, 255, 255, 0.1)"),
    yaxis=dict(gridcolor="rgba(255, 255, 255, 0.06)", zerolinecolor="rgba(255, 255, 255, 0.1)")
)


def plot_revenue_trend(daily_df: pd.DataFrame) -> go.Figure:
    """Renders daily revenue trend line with gradient fill."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(daily_df["date"]),
        y=daily_df["revenue"],
        mode="lines+markers",
        name="Daily Revenue ($)",
        line=dict(color="#38BDF8", width=3),
        marker=dict(size=4, color="#06B6D4"),
        fill="tozeroy",
        fillcolor="rgba(56, 189, 248, 0.08)"
    ))

    # Add 7-day moving average overlay if sufficient days
    if len(daily_df) >= 7:
        roll_7 = daily_df["revenue"].rolling(7).mean()
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(daily_df["date"]),
            y=roll_7,
            mode="lines",
            name="7-Day Moving Avg",
            line=dict(color="#F59E0B", width=2, dash="dash")
        ))

    fig.update_layout(
        title="<b>Daily Sales Revenue Over Time</b>",
        xaxis_title="Date",
        yaxis_title="Net Revenue ($)",
        hovermode="x unified",
        **DARK_LAYOUT
    )
    return fig


def plot_category_distribution(cat_df: pd.DataFrame) -> go.Figure:
    """Renders product category revenue share donut chart."""
    fig = px.pie(
        cat_df,
        values="revenue",
        names="category",
        hole=0.55,
        color_discrete_sequence=["#38BDF8", "#8B5CF6", "#10B981", "#F59E0B", "#F43F5E", "#EC4899"]
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#0A0E1A", width=2))
    )
    fig.update_layout(
        title="<b>Revenue by Product Category</b>",
        showlegend=True,
        **DARK_LAYOUT
    )
    return fig


def plot_regional_comparison(reg_df: pd.DataFrame) -> go.Figure:
    """Renders regional net sales bar chart with color encoding."""
    fig = px.bar(
        reg_df,
        x="region",
        y="revenue",
        color="revenue",
        color_continuous_scale="Tealgrn",
        text="revenue"
    )
    fig.update_traces(
        texttemplate="$%{text:,.0f}",
        textposition="outside",
        marker_line_color="rgba(255, 255, 255, 0.1)",
        marker_line_width=1
    )
    fig.update_layout(
        title="<b>Regional Sales Performance</b>",
        xaxis_title="Region",
        yaxis_title="Total Net Sales ($)",
        coloraxis_showscale=False,
        **DARK_LAYOUT
    )
    return fig


def plot_forecast_with_intervals(history_df: pd.DataFrame, forecast_list: List[Dict[str, Any]]) -> go.Figure:
    """Renders historical actuals joined with future forecast and 95% confidence intervals."""
    fig = go.Figure()

    # Recent historical sales (last 30 days)
    recent_hist = history_df.tail(30).copy()
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(recent_hist["date"]),
        y=recent_hist["revenue"],
        mode="lines+markers",
        name="Historical Actuals",
        line=dict(color="#94A3B8", width=2),
        marker=dict(size=4)
    ))

    if forecast_list:
        fc_df = pd.DataFrame(forecast_list)
        fc_dates = pd.to_datetime(fc_df["forecast_date"])

        # Upper bound
        fig.add_trace(go.Scatter(
            x=fc_dates,
            y=fc_df["upper_bound"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip"
        ))

        # Lower bound with fill to upper
        fig.add_trace(go.Scatter(
            x=fc_dates,
            y=fc_df["lower_bound"],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(16, 185, 129, 0.15)",
            name="95% Confidence Band"
        ))

        # Predicted Sales Line
        fig.add_trace(go.Scatter(
            x=fc_dates,
            y=fc_df["predicted_sales"],
            mode="lines+markers",
            name="7-Day AI Forecast",
            line=dict(color="#10B981", width=3, dash="dot"),
            marker=dict(size=6, color="#34D399")
        ))

    fig.update_layout(
        title="<b>Sales Forecast: Historical Trajectory vs Next 7 Days</b>",
        xaxis_title="Timeline",
        yaxis_title="Sales Revenue ($)",
        hovermode="x unified",
        **DARK_LAYOUT
    )
    return fig


def plot_anomalies_scatter(txns_df: pd.DataFrame) -> go.Figure:
    """Renders transaction distribution highlighting detected outliers."""
    fig = px.scatter(
        txns_df,
        x="quantity",
        y="net_sales",
        color="is_anomaly",
        color_discrete_map={True: "#F43F5E", False: "#38BDF8"},
        hover_data=["transaction_id", "product_name", "category", "unit_price", "discount"],
        size="unit_price",
        size_max=16,
        labels={"is_anomaly": "Flagged Outlier", "net_sales": "Net Sales ($)", "quantity": "Quantity Ordered"}
    )
    fig.update_layout(
        title="<b>Multidimensional Transaction Space (Outliers Highlighted)</b>",
        **DARK_LAYOUT
    )
    return fig


def plot_quality_violations(violations_dict: Dict[str, int]) -> go.Figure:
    """Renders horizontal bar chart of quarantined rule violations."""
    if not violations_dict:
        fig = go.Figure()
        fig.update_layout(title="No quarantined violations detected.", **DARK_LAYOUT)
        return fig

    rules = list(violations_dict.keys())
    counts = list(violations_dict.values())

    fig = px.bar(
        x=counts,
        y=rules,
        orientation="h",
        color=counts,
        color_continuous_scale="Reds",
        labels={"x": "Quarantined Count", "y": "Data Quality Rule Violated"}
    )
    fig.update_layout(
        title="<b>Quarantined Records by Violated Rule</b>",
        coloraxis_showscale=False,
        **DARK_LAYOUT
    )
    return fig
