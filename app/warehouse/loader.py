"""
DataPulse AI - Warehouse Loader Engine
Loads Silver (staging/quarantine) and Gold (Star schema dimensional model) idempotently.
Ensures atomic transactions and deduplication across pipeline reruns.
"""
from datetime import datetime, date
from typing import List, Dict, Any
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.logging import logger
from app.warehouse.models import (
    RawSalesBatch, StagingSales, DataQualityIssue,
    DimDate, DimProduct, DimCustomer, FactSales
)


class WarehouseLoader:
    """Manages transactional data insertion into Silver staging and Gold dimensional tables."""

    def __init__(self, db: Session):
        self.db = db

    def load_staging_and_quarantine(
        self,
        batch_id: str,
        clean_df: pd.DataFrame,
        quarantine_records: List[Dict[str, Any]],
        source: str = "csv",
        source_uri: str = None
    ) -> None:
        """
        Loads cleaned rows into staging_sales and invalid rows into data_quality_issues.
        Idempotent: removes any previous rows for the batch before insertion.
        """
        try:
            # 1. Register or update raw batch record
            batch_record = self.db.query(RawSalesBatch).filter_by(batch_id=batch_id).first()
            if not batch_record:
                batch_record = RawSalesBatch(
                    batch_id=batch_id,
                    source=source,
                    source_uri=source_uri,
                    row_count=len(clean_df) + len(quarantine_records),
                    status="PROCESSING"
                )
                self.db.add(batch_record)
                self.db.flush()

            # 2. Clear existing staging and quarantine records for this batch (Idempotency)
            self.db.query(StagingSales).filter_by(batch_id=batch_id).delete()
            self.db.query(DataQualityIssue).filter_by(batch_id=batch_id).delete()
            self.db.flush()

            # 3. Insert Quarantine records
            for q_data in quarantine_records:
                issue = DataQualityIssue(
                    batch_id=batch_id,
                    transaction_id=q_data.get("transaction_id"),
                    rule_violated=q_data.get("rule_violated", "UNKNOWN"),
                    rejected_value=str(q_data.get("rejected_value", ""))[:255],
                    rejection_reason=q_data.get("rejection_reason", ""),
                    raw_payload=q_data.get("raw_payload", ""),
                    quarantined_at=q_data.get("quarantined_at", datetime.utcnow())
                )
                self.db.add(issue)

            # 4. Insert Staging records
            staging_objs = []
            for _, row in clean_df.iterrows():
                stg = StagingSales(
                    batch_id=batch_id,
                    transaction_id=str(row["transaction_id"]),
                    transaction_date=row["transaction_date"],
                    product_id=str(row["product_id"]),
                    product_name=str(row["product_name"]),
                    category=str(row["category"]),
                    quantity=int(row["quantity"]),
                    unit_price=float(row["unit_price"]),
                    discount=float(row["discount"]),
                    net_sales=float(row["net_sales"]),
                    region=str(row["region"]),
                    customer_id=str(row["customer_id"])
                )
                staging_objs.append(stg)

            if staging_objs:
                self.db.bulk_save_objects(staging_objs)

            self.db.commit()
            logger.info(f"Loaded {len(staging_objs)} staging records and {len(quarantine_records)} quarantine records for batch {batch_id}.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed loading staging/quarantine for batch {batch_id}: {e}")
            raise

    def load_warehouse_gold(self, batch_id: str) -> Dict[str, int]:
        """
        Promotes staging records for batch_id into Gold dimensional warehouse:
        dim_date, dim_product, dim_customer, and fact_sales.
        Safe, idempotent and non-duplicating.
        """
        try:
            staging_rows = self.db.query(StagingSales).filter_by(batch_id=batch_id).all()
            if not staging_rows:
                logger.warning(f"No staging records found for batch {batch_id} to load into Gold warehouse.")
                return {"fact_sales_loaded": 0, "dim_dates": 0, "dim_products": 0, "dim_customers": 0}

            # 1. Update/Populate DimDate
            existing_dates = {d[0] for d in self.db.query(DimDate.full_date).all()}
            new_date_objs = []
            for row in staging_rows:
                t_date = row.transaction_date
                if isinstance(t_date, str):
                    t_date = datetime.strptime(t_date, "%Y-%m-%d").date()
                if t_date not in existing_dates:
                    existing_dates.add(t_date)
                    date_key = int(t_date.strftime("%Y%m%d"))
                    new_date_objs.append(DimDate(
                        date_key=date_key,
                        full_date=t_date,
                        day_of_week=t_date.weekday(),
                        day_name=t_date.strftime("%A"),
                        day_of_month=t_date.day,
                        month=t_date.month,
                        month_name=t_date.strftime("%B"),
                        quarter=(t_date.month - 1) // 3 + 1,
                        year=t_date.year,
                        is_weekend=(t_date.weekday() >= 5)
                    ))
            if new_date_objs:
                self.db.bulk_save_objects(new_date_objs)
                self.db.flush()

            # 2. Update/Populate DimProduct
            existing_products = {p.product_id: p for p in self.db.query(DimProduct).all()}
            for row in staging_rows:
                pid = row.product_id
                if pid not in existing_products:
                    prod = DimProduct(
                        product_id=pid,
                        product_name=row.product_name,
                        category=row.category,
                        first_seen=datetime.utcnow(),
                        last_seen=datetime.utcnow()
                    )
                    self.db.add(prod)
                    existing_products[pid] = prod
                else:
                    existing_products[pid].last_seen = datetime.utcnow()
                    existing_products[pid].product_name = row.product_name
                    existing_products[pid].category = row.category
            self.db.flush()

            # 3. Update/Populate DimCustomer
            existing_customers = {c.customer_id: c for c in self.db.query(DimCustomer).all()}
            for row in staging_rows:
                cid = row.customer_id
                t_date = row.transaction_date
                if isinstance(t_date, str):
                    t_date = datetime.strptime(t_date, "%Y-%m-%d").date()

                if cid not in existing_customers:
                    cust = DimCustomer(
                        customer_id=cid,
                        region=row.region,
                        total_orders=1,
                        first_purchase_date=t_date,
                        last_purchase_date=t_date
                    )
                    self.db.add(cust)
                    existing_customers[cid] = cust
                else:
                    cust = existing_customers[cid]
                    cust.total_orders += 1
                    cust.region = row.region
                    if not cust.first_purchase_date or t_date < cust.first_purchase_date:
                        cust.first_purchase_date = t_date
                    if not cust.last_purchase_date or t_date > cust.last_purchase_date:
                        cust.last_purchase_date = t_date
            self.db.flush()

            # 4. Populate FactSales (Deduplicate / Skip existing transaction_id)
            existing_txns = {
                t[0] for t in self.db.query(FactSales.transaction_id).all()
            }

            fact_objs = []
            for row in staging_rows:
                if row.transaction_id in existing_txns:
                    continue  # Idempotently skip transactions already loaded
                
                t_date = row.transaction_date
                if isinstance(t_date, str):
                    t_date = datetime.strptime(t_date, "%Y-%m-%d").date()
                date_key = int(t_date.strftime("%Y%m%d"))

                fact = FactSales(
                    transaction_id=row.transaction_id,
                    date_key=date_key,
                    product_id=row.product_id,
                    customer_id=row.customer_id,
                    quantity=row.quantity,
                    unit_price=row.unit_price,
                    discount=row.discount,
                    net_sales=row.net_sales,
                    batch_id=batch_id
                )
                fact_objs.append(fact)
                existing_txns.add(row.transaction_id)

            if fact_objs:
                self.db.bulk_save_objects(fact_objs)

            # 5. Update batch status to PROCESSED
            batch_record = self.db.query(RawSalesBatch).filter_by(batch_id=batch_id).first()
            if batch_record:
                batch_record.status = "PROCESSED"

            self.db.commit()
            logger.info(f"Gold warehouse loaded for batch {batch_id}: {len(fact_objs)} facts inserted.")
            return {
                "fact_sales_loaded": len(fact_objs),
                "dim_dates": len(new_date_objs),
                "dim_products": len(existing_products),
                "dim_customers": len(existing_customers)
            }
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed loading Gold warehouse for batch {batch_id}: {e}")
            raise
