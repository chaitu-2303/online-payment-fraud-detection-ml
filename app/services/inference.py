import json
from pathlib import Path
from typing import Dict, Any

import joblib
import pandas as pd

ART = Path("ml/artifacts")

_pipeline = None
_threshold = None

FEATURE_COLS = [
    "amount",
    "transaction_time",
    "device_type",
    "location",
    "payment_method",
    "merchant_category",
    "transaction_frequency",
    "account_age_days",
    "avg_transaction_amount",
    "failed_transactions_24h",
    "is_international",
    "device_change",
]


def _load_model():
    global _pipeline, _threshold
    if _pipeline is None:
        _pipeline = joblib.load(ART / "pipeline.pkl")
        _threshold = json.loads((ART / "threshold.json").read_text())["threshold"]


def get_model_metrics() -> Dict[str, Any]:
    metrics_path = ART / "model_metrics.json"
    if metrics_path.exists():
        return json.loads(metrics_path.read_text())
    return {}


def predict_one(txn: dict) -> Dict[str, Any]:
    _load_model()

    row = {}
    for col in FEATURE_COLS:
        row[col] = txn.get(col, 0)

    row["amount"] = float(row.get("amount", 0))
    row["transaction_time"] = int(row.get("transaction_time", 12))
    row["transaction_frequency"] = int(row.get("transaction_frequency", 5))
    row["account_age_days"] = int(row.get("account_age_days", 365))
    row["avg_transaction_amount"] = float(row.get("avg_transaction_amount", 0))
    row["failed_transactions_24h"] = int(row.get("failed_transactions_24h", 0))
    row["is_international"] = int(row.get("is_international", 0))
    row["device_change"] = int(row.get("device_change", 0))

    df = pd.DataFrame([row])
    proba = float(_pipeline.predict_proba(df)[:, 1][0])

    return {
        "fraud_probability": round(proba, 4),
        "is_fraud": bool(proba >= _threshold),
        "threshold": _threshold,
    }