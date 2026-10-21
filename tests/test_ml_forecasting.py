"""
DataPulse AI - Unit Tests for Machine Learning Sales Forecasting
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.ml.features import TimeSeriesFeatureEngineer
from app.ml.forecasting import SalesForecaster


def generate_mock_daily_series(days: int = 40):
    """Generates continuous daily sales time-series with weekend uplift."""
    start = datetime(2024, 1, 1)
    rows = []
    for i in range(days):
        dt = start + timedelta(days=i)
        base = 2000.0 + (i * 15.0)
        weekend_boost = 600.0 if dt.weekday() >= 5 else 0.0
        rows.append({"date": dt.strftime("%Y-%m-%d"), "revenue": round(base + weekend_boost, 2)})
    return pd.DataFrame(rows)


def test_time_series_feature_engineering_no_leakage():
    """Verifies lag features strictly prevent target leakage."""
    daily_df = generate_mock_daily_series(30)
    feat_df = TimeSeriesFeatureEngineer.build_daily_features(daily_df)

    # lag_1 for index i must strictly equal revenue at index i-1
    for i in range(1, len(feat_df)):
        assert feat_df.loc[i, "lag_1"] == feat_df.loc[i - 1, "revenue"]


def test_sales_forecaster_train_and_predict():
    """Verifies end-to-end model training, out-of-sample evaluation, and 7-day multi-step predictions."""
    daily_df = generate_mock_daily_series(45)
    forecaster = SalesForecaster()
    metrics = forecaster.train_and_evaluate(daily_df, test_days=10)

    assert "ml_model" in metrics
    assert "baseline" in metrics
    assert metrics["ml_model"]["mae"] > 0.0
    assert metrics["ml_model"]["rmse"] > 0.0

    forecasts = forecaster.predict_next_7_days(daily_df)
    assert len(forecasts) == 7

    for step, fc in enumerate(forecasts):
        assert "predicted_sales" in fc
        assert fc["predicted_sales"] >= 0.0
        assert fc["lower_bound"] <= fc["predicted_sales"] <= fc["upper_bound"]
