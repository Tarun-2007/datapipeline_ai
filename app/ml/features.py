"""
DataPulse AI - Machine Learning Feature Engineering
Constructs time-series lag and rolling window features for sales forecasting,
and tabular statistical features for transaction anomaly detection.
"""
from typing import Tuple, List, Optional
import pandas as pd
import numpy as np


class TimeSeriesFeatureEngineer:
    """Extracts leakage-free temporal, lagged, and rolling features for forecasting."""

    @staticmethod
    def build_daily_features(daily_df: pd.DataFrame) -> pd.DataFrame:
        """
        Takes a dataframe with columns ['date', 'revenue'] (daily aggregated),
        sorts chronologically, and engineers time-series features.
        
        Args:
            daily_df: DataFrame containing 'date' (YYYY-MM-DD) and 'revenue' (float).
            
        Returns:
            pd.DataFrame: Engineered feature matrix with no target leakage.
        """
        df = daily_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Calendar features
        df["day_of_week"] = df["date"].dt.dayofweek
        df["day_of_month"] = df["date"].dt.day
        df["month"] = df["date"].dt.month
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # Strictly shifted lag features to prevent lookahead target leakage
        df["lag_1"] = df["revenue"].shift(1)
        df["lag_2"] = df["revenue"].shift(2)
        df["lag_7"] = df["revenue"].shift(7)
        df["lag_14"] = df["revenue"].shift(14)

        # Rolling window features based on strictly lagged revenue
        df["roll_mean_7"] = df["revenue"].shift(1).rolling(window=7, min_periods=3).mean()
        df["roll_std_7"] = df["revenue"].shift(1).rolling(window=7, min_periods=3).std()
        df["roll_mean_14"] = df["revenue"].shift(1).rolling(window=14, min_periods=7).mean()

        # Fill early rolling std NaNs with 0
        df["roll_std_7"] = df["roll_std_7"].fillna(0.0)

        # Drop rows where essential 7-day lags are unavailable
        clean_df = df.dropna(subset=["lag_1", "lag_7", "roll_mean_7"]).reset_index(drop=True)
        return clean_df

    @staticmethod
    def get_feature_columns() -> List[str]:
        """Returns standard feature column names for the forecasting model."""
        return [
            "day_of_week",
            "day_of_month",
            "month",
            "is_weekend",
            "lag_1",
            "lag_2",
            "lag_7",
            "lag_14",
            "roll_mean_7",
            "roll_std_7",
            "roll_mean_14"
        ]


class AnomalyFeatureEngineer:
    """Extracts behavioral and financial ratio features for Isolation Forest anomaly scoring."""

    @staticmethod
    def extract_transaction_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Extracts numeric tabular features from transaction records.
        """
        data = df.copy()
        feature_cols = ["quantity", "unit_price", "discount", "net_sales"]
        
        # Clean numeric nulls or invalid types
        for col in feature_cols:
            data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0.0)

        # Derived interaction features
        data["discount_amount"] = (data["quantity"] * data["unit_price"] * data["discount"]).round(2)
        feature_cols.append("discount_amount")

        return data, feature_cols
