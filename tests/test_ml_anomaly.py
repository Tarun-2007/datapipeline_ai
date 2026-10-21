"""
DataPulse AI - Unit Tests for Isolation Forest Sales Anomaly Detection
"""
import pytest
import pandas as pd
from app.ml.anomaly import SalesAnomalyDetector
from app.ingestion.generator import SalesDataGenerator


def test_anomaly_detection_training_and_scoring():
    """Verifies Isolation Forest trains and tags anomalous outliers with explanatory rationale."""
    gen = SalesDataGenerator(seed=77)
    df = gen.generate_records(num_records=150, dirty_rate=0.0)

    # Inject deliberate extreme transaction outlier
    df.loc[0, "quantity"] = 50
    df.loc[0, "unit_price"] = 999.0
    df.loc[0, "net_sales"] = 49950.0

    detector = SalesAnomalyDetector(contamination=0.04)
    metrics = detector.train(df)

    assert metrics["model_type"] == "IsolationForest"
    assert metrics["samples_trained"] == 150

    scored = detector.detect_anomalies(df)
    assert "is_anomaly" in scored.columns
    assert "anomaly_score" in scored.columns
    assert "explanation" in scored.columns

    # The extreme transaction must be flagged as anomaly
    assert bool(scored.loc[0, "is_anomaly"]) is True
    assert "High net sales" in scored.loc[0, "explanation"] or "Unusually large quantity" in scored.loc[0, "explanation"]
