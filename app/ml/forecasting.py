"""
DataPulse AI - Sales Forecasting Engine
Trains, validates, and forecasts daily sales using a leak-free Random Forest Regressor
compared against a baseline moving-average benchmark on time-based validation splits.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from app.core.config import settings
from app.core.logging import logger
from app.ml.features import TimeSeriesFeatureEngineer

MODEL_FILE = settings.MODEL_DIR / "sales_forecaster.joblib"


class SalesForecaster:
    """End-to-end sales forecasting model with time-based validation and recursive 7-day multi-step prediction."""

    def __init__(self):
        self.model = None
        self.metrics: Dict[str, Any] = {}
        self.feature_cols = TimeSeriesFeatureEngineer.get_feature_columns()
        self.is_synthetic_demonstration = True

    def train_and_evaluate(
        self,
        daily_df: pd.DataFrame,
        test_days: int = 14
    ) -> Dict[str, Any]:
        """
        Engineers features, splits on chronological boundary, evaluates baseline vs Random Forest,
        and persists the trained model artifact.
        
        Args:
            daily_df: DataFrame with 'date' and 'revenue'
            test_days: Number of recent days reserved strictly for out-of-sample testing
        """
        if len(daily_df) < 25:
            raise ValueError(f"Insufficient historical data ({len(daily_df)} days). Minimum 25 days required.")

        # 1. Feature Engineering (no target leakage)
        feat_df = TimeSeriesFeatureEngineer.build_daily_features(daily_df)
        if len(feat_df) < 15:
            raise ValueError("Insufficient records after lag-window construction.")

        # 2. Chronological Train/Test Split (Strictly avoid random k-fold shuffle!)
        split_idx = max(len(feat_df) - test_days, int(len(feat_df) * 0.75))
        train_df = feat_df.iloc[:split_idx].copy()
        test_df = feat_df.iloc[split_idx:].copy()

        X_train = train_df[self.feature_cols]
        y_train = train_df["revenue"]
        X_test = test_df[self.feature_cols]
        y_test = test_df["revenue"]

        # 3. Baseline Model: 7-day rolling mean (or lag_7)
        # Using lag_7 as a seasonal baseline benchmark
        baseline_preds = test_df["lag_7"].values
        base_mae = float(mean_absolute_error(y_test, baseline_preds))
        base_rmse = float(np.sqrt(mean_squared_error(y_test, baseline_preds)))

        # 4. Machine Learning Model: Random Forest Regressor
        rf = RandomForestRegressor(
            n_estimators=100,
            max_depth=6,
            min_samples_split=4,
            random_state=42
        )
        rf.fit(X_train, y_train)
        rf_preds = rf.predict(X_test)

        rf_mae = float(mean_absolute_error(y_test, rf_preds))
        rf_rmse = float(np.sqrt(mean_squared_error(y_test, rf_preds)))
        rf_mape = float(np.mean(np.abs((y_test.values - rf_preds) / np.maximum(y_test.values, 1.0)))) * 100.0

        improvement_pct = round(((base_mae - rf_mae) / base_mae) * 100, 2) if base_mae > 0 else 0.0

        self.model = rf
        self.metrics = {
            "model_type": "RandomForestRegressor",
            "train_samples": len(train_df),
            "test_samples": len(test_df),
            "trained_at": datetime.utcnow().isoformat(),
            "baseline": {
                "benchmark_name": "7-Day Seasonal Lag",
                "mae": round(base_mae, 2),
                "rmse": round(base_rmse, 2)
            },
            "ml_model": {
                "mae": round(rf_mae, 2),
                "rmse": round(rf_rmse, 2),
                "mape_pct": round(rf_mape, 2),
                "mae_improvement_over_baseline_pct": improvement_pct
            },
            "features_used": self.feature_cols,
            "disclaimer": "Forecast is trained on synthetic sales data for algorithmic demonstration purposes."
        }

        # 5. Persist Model Artifact
        self.save_model()
        logger.info(f"Sales Forecaster trained: RF MAE={rf_mae:.2f} vs Base MAE={base_mae:.2f} ({improvement_pct}% gain).")
        return self.metrics

    def predict_next_7_days(self, daily_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Generates recursive 7-day multi-step sales predictions starting from the day after the last historical date.
        """
        if self.model is None:
            if not self.load_model():
                # Train model on provided daily_df if not yet trained
                self.train_and_evaluate(daily_df)

        feat_df = TimeSeriesFeatureEngineer.build_daily_features(daily_df)
        if feat_df.empty:
            raise ValueError("Insufficient daily data to construct forecast features.")

        # Start from the most recent known date
        last_date = pd.to_datetime(daily_df["date"]).max()
        history = daily_df.sort_values("date").copy()

        forecasts = []
        current_history = history.copy()

        for step in range(1, 8):
            target_date = last_date + timedelta(days=step)
            # Reconstruct feature dataframe up to current simulated date
            temp_feat = TimeSeriesFeatureEngineer.build_daily_features(current_history)
            latest_row = temp_feat.iloc[-1:][self.feature_cols]

            pred_val = float(self.model.predict(latest_row)[0])
            pred_val = max(round(pred_val, 2), 0.0)

            # Estimate 95% confidence intervals based on model test RMSE
            rmse_val = self.metrics.get("ml_model", {}).get("rmse", pred_val * 0.15)
            lower_bound = max(round(pred_val - 1.96 * rmse_val, 2), 0.0)
            upper_bound = round(pred_val + 1.96 * rmse_val, 2)

            forecasts.append({
                "forecast_date": target_date.strftime("%Y-%m-%d"),
                "predicted_sales": pred_val,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "model_type": "RandomForestRegressor"
            })

            # Append prediction to history to allow recursive multi-step forecasting
            new_row = pd.DataFrame([{
                "date": target_date.strftime("%Y-%m-%d"),
                "revenue": pred_val
            }])
            current_history = pd.concat([current_history, new_row], ignore_index=True)

        return forecasts

    def save_model(self, path: Optional[Path] = None) -> None:
        """Saves model and metadata to disk."""
        save_path = path or MODEL_FILE
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "metrics": self.metrics,
            "feature_cols": self.feature_cols
        }, save_path)

    def load_model(self, path: Optional[Path] = None) -> bool:
        """Loads model and metadata from disk if available."""
        load_path = path or MODEL_FILE
        if not load_path.exists():
            return False
        try:
            artifact = joblib.load(load_path)
            self.model = artifact["model"]
            self.metrics = artifact["metrics"]
            self.feature_cols = artifact["feature_cols"]
            return True
        except Exception as e:
            logger.warning(f"Could not load forecast model: {e}")
            return False
