"""
DataPulse AI - Dashboard Metric Cards & Presentation UI Components
"""
import streamlit as st


def render_header(title: str, subtitle: str, badge: str = None) -> None:
    """Renders consistent page header with subtitle and optional badge."""
    badge_html = f'<span class="badge badge-info" style="margin-left: 12px; vertical-align: middle;">{badge}</span>' if badge else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 24px;">
            <h1 style="font-size: 2.1rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 6px; display: inline-block;">
                {title}
            </h1>
            {badge_html}
            <p style="color: #94A3B8; font-size: 0.95rem; margin: 0; line-height: 1.5;">
                {subtitle}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    badge_text: str = None,
    badge_type: str = "success"
) -> None:
    """Renders styled KPI card with optional colored status pill."""
    badge_html = f'<div style="float: right;"><span class="badge badge-{badge_type}">{badge_text}</span></div>' if badge_text else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            {badge_html}
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
