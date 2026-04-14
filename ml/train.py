import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA_PATH = Path("data/fraud_data.csv")
ART_DIR = Path("ml/artifacts")
ART_DIR.mkdir(parents=True, exist_ok=True)

print(f"Loading dataset from {DATA_PATH} ...")
df = pd.read_csv(DATA_PATH)
print(f"Dataset shape: {df.shape}")
print(f"Fraud distribution:\n{df['is_fraud'].value_counts()}\n")

feature_cols = [
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

X = df[feature_cols]
y = df["is_fraud"]

num_cols = [
    "amount",
    "transaction_time",
    "transaction_frequency",
    "account_age_days",
    "avg_transaction_amount",
    "failed_transactions_24h",
]
cat_cols = [
    "device_type",
    "location",
    "payment_method",
    "merchant_category",
    "is_international",
    "device_change",
]

preprocess = ColumnTransformer(
    [
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
    ]
)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

print("Preprocessing training data ...")
X_train_processed = preprocess.fit_transform(X_train)
X_test_processed = preprocess.transform(X_test)

print("Applying SMOTE to balance classes ...")
smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train_processed, y_train)
print(f"After SMOTE: {pd.Series(y_train_resampled).value_counts().to_dict()}")

model = RandomForestClassifier(
    n_estimators=200,
    max_depth=20,
    min_samples_split=4,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)

print("\nTraining Random Forest (200 trees) ...")
model.fit(X_train_resampled, y_train_resampled)

pipeline = Pipeline([("preprocess", preprocess), ("model", model)])

y_pred = model.predict(X_test_processed)
y_proba = model.predict_proba(X_test_processed)[:, 1]

threshold = 0.45

y_pred_threshold = (y_proba >= threshold).astype(int)

acc = accuracy_score(y_test, y_pred_threshold)
prec = precision_score(y_test, y_pred_threshold, zero_division=0)
rec = recall_score(y_test, y_pred_threshold, zero_division=0)
f1 = f1_score(y_test, y_pred_threshold, zero_division=0)
cm = confusion_matrix(y_test, y_pred_threshold).tolist()

print("\n========== MODEL EVALUATION ==========")
print(f"Threshold: {threshold}")
print(f"Accuracy:  {acc:.4f}")
print(f"Precision: {prec:.4f}")
print(f"Recall:    {rec:.4f}")
print(f"F1 Score:  {f1:.4f}")
print(f"\nConfusion Matrix:\n{np.array(cm)}")
print(f"\n{classification_report(y_test, y_pred_threshold, zero_division=0)}")

joblib.dump(pipeline, ART_DIR / "pipeline.pkl")
(ART_DIR / "threshold.json").write_text(json.dumps({"threshold": threshold}))

metrics = {
    "model": "RandomForestClassifier",
    "n_estimators": 200,
    "dataset_rows": len(df),
    "features": feature_cols,
    "accuracy": round(acc, 4),
    "precision": round(prec, 4),
    "recall": round(rec, 4),
    "f1_score": round(f1, 4),
    "confusion_matrix": cm,
    "threshold": threshold,
    "resampling": "SMOTE",
}
(ART_DIR / "model_metrics.json").write_text(json.dumps(metrics, indent=2))

print("\nModel saved to ml/artifacts/pipeline.pkl")
print("Threshold saved to ml/artifacts/threshold.json")
print("Metrics saved to ml/artifacts/model_metrics.json")
print("Done!")