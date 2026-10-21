"""
DataPulse AI - Data Validation and Quarantine Engine
Performs schema conformance checks, business rule validations, anomaly quarantine,
and deduplication without silent record deletion.
"""
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from app.core.logging import logger

REQUIRED_COLUMNS = [
    "transaction_id",
    "transaction_date",
    "product_id",
    "product_name",
    "category",
    "quantity",
    "unit_price",
    "discount",
    "region",
    "customer_id"
]


class ValidationResult:
    """Encapsulates the outcome of data validation."""
    def __init__(
        self,
        valid_df: pd.DataFrame,
        quarantine_records: List[Dict[str, Any]],
        total_input: int,
        duplicate_count: int
    ):
        self.valid_df = valid_df
        self.quarantine_records = quarantine_records
        self.total_input = total_input
        self.accepted_count = len(valid_df)
        self.rejected_count = len(quarantine_records)
        self.duplicate_count = duplicate_count
        self.rejection_rate = (
            round(self.rejected_count / total_input, 4) if total_input > 0 else 0.0
        )

    def summary_dict(self) -> Dict[str, Any]:
        """Provides high-level metrics for reporting and monitoring."""
        return {
            "total_input": self.total_input,
            "accepted_records": self.accepted_count,
            "quarantined_records": self.rejected_count,
            "duplicate_records": self.duplicate_count,
            "rejection_rate_pct": round(self.rejection_rate * 100, 2),
            "status": "PASSED" if self.rejection_rate <= 0.20 else "WARNING_HIGH_REJECTIONS"
        }


class DataValidator:
    """Validates raw sales datasets against strict data engineering and business rules."""

    def __init__(self, batch_id: str):
        self.batch_id = batch_id

    def validate_schema(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Verifies all mandatory columns exist in the incoming dataframe."""
        missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            return False, missing
        return True, []

    def validate_and_quarantine(self, df: pd.DataFrame) -> ValidationResult:
        """
        Executes granular validation rules on each row.
        Valid rows are routed to the clean dataframe.
        Invalid rows are tagged with detailed rejection reasons and routed to quarantine.
        """
        total_input = len(df)
        if total_input == 0:
            return ValidationResult(pd.DataFrame(columns=REQUIRED_COLUMNS), [], 0, 0)

        # Check required schema
        schema_ok, missing_cols = self.validate_schema(df)
        if not schema_ok:
            raise ValueError(f"Batch {self.batch_id} schema violation. Missing columns: {missing_cols}")

        quarantine_list: List[Dict[str, Any]] = []
        valid_rows: List[Dict[str, Any]] = []
        seen_txn_ids = set()
        duplicate_count = 0

        # Iterate over records as dicts to preserve original payload for quarantine inspection
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            txn_id = row_dict.get("transaction_id")
            raw_payload_json = json.dumps(row_dict, default=str)

            # Rule 1: Missing primary transaction ID
            if pd.isna(txn_id) or str(txn_id).strip() == "":
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": None,
                    "rule_violated": "MISSING_TRANSACTION_ID",
                    "rejected_value": str(txn_id),
                    "rejection_reason": "Transaction ID is null, empty or missing",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            txn_id_str = str(txn_id).strip()

            # Rule 2: Duplicate transaction ID within batch (deduplication on business key)
            if txn_id_str in seen_txn_ids:
                duplicate_count += 1
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": txn_id_str,
                    "rule_violated": "DUPLICATE_TRANSACTION_ID",
                    "rejected_value": txn_id_str,
                    "rejection_reason": f"Duplicate transaction_id '{txn_id_str}' encountered in batch",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            # Rule 3: Missing essential dimensional identifiers (customer_id, product_id)
            cust_id = row_dict.get("customer_id")
            if pd.isna(cust_id) or str(cust_id).strip() == "":
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": txn_id_str,
                    "rule_violated": "MISSING_CUSTOMER_ID",
                    "rejected_value": str(cust_id),
                    "rejection_reason": "Customer ID cannot be null or empty",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            prod_id = row_dict.get("product_id")
            if pd.isna(prod_id) or str(prod_id).strip() == "":
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": txn_id_str,
                    "rule_violated": "MISSING_PRODUCT_ID",
                    "rejected_value": str(prod_id),
                    "rejection_reason": "Product ID cannot be null or empty",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            # Rule 4: Date parsing validity
            raw_date = row_dict.get("transaction_date")
            try:
                parsed_date = pd.to_datetime(raw_date)
                if pd.isna(parsed_date):
                    raise ValueError("Date is NaT")
            except Exception:
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": txn_id_str,
                    "rule_violated": "INVALID_DATE_FORMAT",
                    "rejected_value": str(raw_date),
                    "rejection_reason": f"Transaction date '{raw_date}' is not a valid date format",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            # Rule 5: Quantity validation (must be positive integer > 0)
            try:
                qty = int(row_dict.get("quantity"))
                if qty <= 0:
                    quarantine_list.append({
                        "batch_id": self.batch_id,
                        "transaction_id": txn_id_str,
                        "rule_violated": "NON_POSITIVE_QUANTITY",
                        "rejected_value": str(qty),
                        "rejection_reason": f"Quantity must be greater than zero, received {qty}",
                        "raw_payload": raw_payload_json,
                        "quarantined_at": datetime.utcnow()
                    })
                    continue
            except (ValueError, TypeError):
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": txn_id_str,
                    "rule_violated": "INVALID_QUANTITY_TYPE",
                    "rejected_value": str(row_dict.get("quantity")),
                    "rejection_reason": "Quantity is not a valid integer",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            # Rule 6: Unit price validation (must be positive float > 0.0)
            try:
                price = float(row_dict.get("unit_price"))
                if price <= 0.0:
                    quarantine_list.append({
                        "batch_id": self.batch_id,
                        "transaction_id": txn_id_str,
                        "rule_violated": "NON_POSITIVE_PRICE",
                        "rejected_value": str(price),
                        "rejection_reason": f"Unit price must be strictly positive, received {price}",
                        "raw_payload": raw_payload_json,
                        "quarantined_at": datetime.utcnow()
                    })
                    continue
            except (ValueError, TypeError):
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": txn_id_str,
                    "rule_violated": "INVALID_PRICE_TYPE",
                    "rejected_value": str(row_dict.get("unit_price")),
                    "rejection_reason": "Unit price is not a valid numeric float",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            # Rule 7: Discount range validation (must be 0.0 <= discount < 1.0)
            try:
                discount = float(row_dict.get("discount", 0.0))
                if discount < 0.0 or discount >= 1.0:
                    quarantine_list.append({
                        "batch_id": self.batch_id,
                        "transaction_id": txn_id_str,
                        "rule_violated": "INVALID_DISCOUNT_RANGE",
                        "rejected_value": str(discount),
                        "rejection_reason": f"Discount must be between 0.0 and 1.0 (non-inclusive), received {discount}",
                        "raw_payload": raw_payload_json,
                        "quarantined_at": datetime.utcnow()
                    })
                    continue
            except (ValueError, TypeError):
                quarantine_list.append({
                    "batch_id": self.batch_id,
                    "transaction_id": txn_id_str,
                    "rule_violated": "INVALID_DISCOUNT_TYPE",
                    "rejected_value": str(row_dict.get("discount")),
                    "rejection_reason": "Discount is not a valid numeric float",
                    "raw_payload": raw_payload_json,
                    "quarantined_at": datetime.utcnow()
                })
                continue

            # Record passed all validation checks
            seen_txn_ids.add(txn_id_str)
            valid_rows.append(row_dict)

        valid_df = pd.DataFrame(valid_rows) if valid_rows else pd.DataFrame(columns=REQUIRED_COLUMNS)
        logger.info(
            f"Batch {self.batch_id} validation: {total_input} in, {len(valid_df)} accepted, "
            f"{len(quarantine_list)} quarantined, {duplicate_count} duplicates."
        )

        return ValidationResult(
            valid_df=valid_df,
            quarantine_records=quarantine_list,
            total_input=total_input,
            duplicate_count=duplicate_count
        )
