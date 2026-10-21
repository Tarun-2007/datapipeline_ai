"""
DataPulse AI - Sales Anomaly Detection Engine
Detects irregular, outlier, or potentially fraudulent sales transactions using
Isolation Forest unsupervised learning, with transparent rule-based explanation generators.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.core.logging import logger
from app.ml.features import AnomalyFeatureEngineer

MODEL_FILE = settings.MODEL_DIR / "anomaly_detector.joblib"


class SalesAnomalyDetector:
    """Unsupervised anomaly detection on multidimensional transaction vectors."""

    def __init__(self, contamination: float = 0.03):
        self.contamination = contamination
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_cols: List[str] = []
        self.metrics: Dict[str, Any] = {}

    def train(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Trains Isolation Forest and StandardScaler on historical clean sales transactions.
        """
        if len(df) < 50:
            raise ValueError(f"Insufficient transactions ({len(df)}) to train anomaly detector. Minimum 50 required.")

        featured_df, feature_cols = AnomalyFeatureEngineer.extract_transaction_features(df)
        self.feature_cols = feature_cols

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(featured_df[self.feature_cols])

        iso = IsolationForest(
            n_estimators=100,
            contamination=self.contamination,
            random_state=42,
            n_jobs=-1
        )
        iso.fit(X_scaled)

        self.model = iso
        self.scaler = scaler
        self.metrics = {
            "model_type": "IsolationForest",
            "samples_trained": len(df),
            "contamination_rate": self.contamination,
            "trained_at": datetime.utcnow().isoformat(),
            "features_used": self.feature_cols,
            "limitations": [
                "Unsupervised model: does not differentiate between legitimate high-value VIP orders and data anomalies.",
                "Sensitivity is dependent on contamination hyperparameter calibration.",
                "Assumes continuous numerical metrics with near-stationary distribution."
            ]
        }

        self.save_model()
        logger.info(f"Anomaly Detector trained on {len(df)} transactions (contamination={self.contamination}).")
        return self.metrics

    def detect_anomalies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Scores transactions and flags anomalies (is_anomaly=True where prediction == -1).
        Generates contextual natural-language explanations for flagged records.
        """
        if self.model is None or self.scaler is None:
            if not self.load_model():
                self.train(df)

        featured_df, _ = AnomalyFeatureEngineer.extract_transaction_features(df)
        X_scaled = self.scaler.transform(featured_df[self.feature_cols])

        # Isolation forest: -1 is anomaly, 1 is inlier
        preds = self.model.predict(X_scaled)
        # Decision function: lower values mean more anomalous (negative = outlier)
        scores = self.model.decision_function(X_scaled)

        result_df = df.copy()
        result_df["is_anomaly"] = (preds == -1)
        # Invert score to positive anomaly magnitude (higher = more abnormal)
        result_df["anomaly_score"] = (scores.max() - scores).round(4)

        # Generate explanatory tags for why transaction was flagged
        explanations = []
        q95_sales = float(result_df["net_sales"].quantile(0.95))
        q95_qty = float(result_df["quantity"].quantile(0.95))

        for _, row in result_df.iterrows():
            if not row["is_anomaly"]:
                explanations.append("Normal transaction pattern")
                continue

            reasons = []
            if float(row["net_sales"]) >= q95_sales:
                reasons.append(f"High net sales (${row['net_sales']:.2f} >= 95th percentile ${q95_sales:.2f})")
            if int(row["quantity"]) >= q95_qty and int(row["quantity"]) >= 5:
                reasons.append(f"Unusually large quantity ({int(row['quantity'])} units)")
            if float(row["discount"]) >= 0.15:
                reasons.append(f"Deep discount ({int(row['discount']*100)}%) applied")
            if float(row["unit_price"]) >= 300.0:
                reasons.append(f"Premium unit price tier (${row['unit_price']:.2f})")

            if not reasons:
                reasons.append("Unusual multidimensional feature combination")

            explanations.append("; ".join(reasons))

        result_df["explanation"] = explanations
        return result_df

    def save_model(self, path: Optional[Path] = None) -> None:
        """Saves Isolation Forest model, scaler, and metadata to disk."""
        save_path = path or MODEL_FILE
        save_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "feature_cols": self.feature_cols,
            "metrics": self.metrics,
            "contamination": self.contamination
        }, save_path)

    def load_model(self, path: Optional[Path] = None) -> bool:
        """Loads model and scaler from disk."""
        load_path = path or MODEL_FILE
        if not load_path.exists():
            return False
        try:
            artifact = joblib.load(load_path)
            self.model = artifact["model"]
            self.scaler = artifact["scaler"]
            self.feature_cols = artifact["feature_cols"]
            self.metrics = artifact["metrics"]
            self.contamination = artifact.get("contamination", 0.03)
            return True
        except Exception as e:
            logger.warning(f"Could not load anomaly detector: {e}")
            return False
