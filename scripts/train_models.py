import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from app.core.database import SessionLocal
from app.warehouse.analytics import WarehouseAnalytics
from app.warehouse.models import SalesForecast, SalesAnomaly
from app.ml.forecasting import SalesForecaster
from app.ml.anomaly import SalesAnomalyDetector


def main():
    print("=" * 60)
    print("DATAPULSE AI - ML TRAINING WORKFLOW")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Train Sales Forecasting Model
        print("\n[1/2] Training Sales Forecaster (Random Forest Regressor)...")
        daily_data = WarehouseAnalytics.get_daily_revenue(db)
        if len(daily_data) >= 20:
            df_daily = pd.DataFrame(daily_data)
            forecaster = SalesForecaster()
            metrics = forecaster.train_and_evaluate(df_daily)
            forecasts = forecaster.predict_next_7_days(df_daily)

            # Persist in database
            db.query(SalesForecast).delete()
            for fc in forecasts:
                sf = SalesForecast(
                    forecast_date=pd.to_datetime(fc["forecast_date"]).date(),
                    predicted_sales=fc["predicted_sales"],
                    lower_bound=fc["lower_bound"],
                    upper_bound=fc["upper_bound"],
                    model_type=fc["model_type"],
                    mae=metrics.get("ml_model", {}).get("mae"),
                    rmse=metrics.get("ml_model", {}).get("rmse")
                )
                db.add(sf)
            db.commit()

            print(f"  -> Model trained successfully!")
            print(f"  -> Baseline 7-Day Lag MAE:  ${metrics['baseline']['mae']:.2f}")
            print(f"  -> Random Forest Test MAE:  ${metrics['ml_model']['mae']:.2f}")
            print(f"  -> Random Forest Test RMSE: ${metrics['ml_model']['rmse']:.2f}")
            print(f"  -> Improvement over Base:   {metrics['ml_model']['mae_improvement_over_baseline_pct']}%")
            print(f"  -> Generated 7-day future predictions persisted.")
        else:
            print(f"  -> Warning: Insufficient daily data ({len(daily_data)} days). Need >= 20 days. Skipping forecast training.")

        # 2. Train Sales Anomaly Detector
        print("\n[2/2] Training Sales Anomaly Detector (Isolation Forest)...")
        txns = WarehouseAnalytics.get_recent_transactions(db, limit=5000)
        if len(txns) >= 50:
            df_txns = pd.DataFrame(txns)
            detector = SalesAnomalyDetector()
            det_metrics = detector.train(df_txns)
            scored_df = detector.detect_anomalies(df_txns)

            anomalies = scored_df[scored_df["is_anomaly"]].copy()
            db.query(SalesAnomaly).delete()
            for _, row in anomalies.iterrows():
                anom = SalesAnomaly(
                    transaction_id=str(row["transaction_id"]),
                    transaction_date=pd.to_datetime(row["transaction_date"]).date(),
                    product_id=str(row["product_id"]),
                    category=str(row["category"]),
                    region=str(row["region"]),
                    quantity=int(row["quantity"]),
                    unit_price=float(row["unit_price"]),
                    net_sales=float(row["net_sales"]),
                    anomaly_score=float(row["anomaly_score"]),
                    is_anomaly=True,
                    explanation=str(row["explanation"])
                )
                db.add(anom)
            db.commit()

            print(f"  -> Anomaly detector trained successfully on {len(df_txns)} transactions!")
            print(f"  -> Identified {len(anomalies)} anomalous records ({len(anomalies)/len(df_txns)*100:.1f}%).")
            print(f"  -> Outliers and diagnostic explanations saved to database.")
        else:
            print(f"  -> Warning: Insufficient transactions ({len(txns)}). Need >= 50. Skipping anomaly detection.")

        print("\n" + "=" * 60)
        print("ML TRAINING COMPLETE - ALL ARTIFACTS SAVED")
        print("=" * 60)
    finally:
        db.close()


if __name__ == "__main__":
    main()
