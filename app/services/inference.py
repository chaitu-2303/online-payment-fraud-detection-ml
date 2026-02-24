import json
from pathlib import Path
import joblib
import pandas as pd

ART = Path("ml/artifacts")
pipeline = joblib.load(ART / "pipeline.pkl")
threshold = json.loads((ART / "threshold.json").read_text())["threshold"]

def predict_one(txn: dict):
    df = pd.DataFrame([txn])
    proba = float(pipeline.predict_proba(df)[:, 1][0])
    return {
        "fraud_probability": proba,
        "is_fraud": bool(proba >= threshold),
        "threshold": threshold
    }