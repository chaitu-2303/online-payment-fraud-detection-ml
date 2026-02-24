import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

DATA_PATH = Path("data/onlinefraud.csv")
ART_DIR = Path("ml/artifacts")
ART_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_PATH)

X = df.drop("is_fraud", axis=1)
y = df["is_fraud"]

num_cols = ["amount"]
cat_cols = [
    "payment_method", "merchant_category",
    "transaction_time", "device_new", "location_change"
]

preprocess = ColumnTransformer([
    ("num", StandardScaler(), num_cols),
    ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
])

model = LogisticRegression(class_weight="balanced")

pipeline = Pipeline([
    ("preprocess", preprocess),
    ("model", model)
])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

pipeline.fit(X_train, y_train)

joblib.dump(pipeline, ART_DIR / "pipeline.pkl")
(ART_DIR / "threshold.json").write_text(json.dumps({"threshold": 0.5}))

print("Model trained and saved")