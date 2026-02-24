from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.inference import predict_one  # your ML pipeline inference

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ---------- Fake user (keep until you plug real login) ----------
def get_current_user() -> dict:
    # Replace later with real auth/session logic
    return {"username": "Guest", "role": "user"}


# ---------- CSV loading ----------
BASE_DIR = Path(__file__).resolve().parents[2]  # project_root/app/routes/pages.py -> project_root
CSV_PATH = BASE_DIR / "data" / "onlinefraud.csv"

_cached_df: pd.DataFrame | None = None


def load_df() -> pd.DataFrame:
    global _cached_df
    if _cached_df is None:
        if not CSV_PATH.exists():
            raise FileNotFoundError(f"CSV not found at: {CSV_PATH}")
        df = pd.read_csv(CSV_PATH)

        # Normalize columns safely
        df["payment_method"] = df["payment_method"].astype(str).str.strip()
        df["merchant_category"] = df["merchant_category"].astype(str).str.strip()
        df["transaction_time"] = df["transaction_time"].astype(str).str.strip()

        df["device_new"] = pd.to_numeric(df["device_new"], errors="coerce").fillna(0).astype(int)
        df["location_change"] = pd.to_numeric(df["location_change"], errors="coerce").fillna(0).astype(int)
        df["is_fraud"] = pd.to_numeric(df["is_fraud"], errors="coerce").fillna(0).astype(int)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

        # Add txn_id if CSV doesn't have it
        df = df.reset_index(drop=True)
        df["txn_id"] = df.index + 1

        _cached_df = df
    return _cached_df


def format_inr(n: float) -> str:
    n_int = int(round(float(n)))
    s = str(n_int)
    if len(s) <= 3:
        return s
    last3 = s[-3:]
    rest = s[:-3]
    out = ""
    while len(rest) > 2:
        out = "," + rest[-2:] + out
        rest = rest[:-2]
    if rest:
        out = rest + out
    return out + "," + last3


def compute_risk_level(prob: float) -> str:
    if prob < 0.33:
        return "Low"
    if prob < 0.66:
        return "Medium"
    return "High"


def build_reasons(
    prob: float,
    amount: float,
    device_new: int,
    location_change: int,
    time: str,
    payment_method: str,
    merchant_category: str,
) -> list[str]:
    reasons: list[str] = []

    if amount >= 200000:
        reasons.append("High transaction amount increases risk.")
    elif amount >= 50000:
        reasons.append("Medium-high amount can be suspicious depending on behavior.")
    else:
        reasons.append("Amount looks normal for regular spending.")

    if device_new == 1:
        reasons.append("New device detected (unusual device).")
    else:
        reasons.append("Same device used (usually safer).")

    if location_change == 1:
        reasons.append("Location change detected (unusual location).")
    else:
        reasons.append("Same location (supports a normal pattern).")

    if "night" in str(time).lower():
        reasons.append("Night-time transactions can have slightly higher risk.")
    else:
        reasons.append("Day-time transactions are more common for normal users.")

    if "net" in str(payment_method).lower():
        reasons.append("NetBanking can be riskier for some patterns.")
    if "finance" in str(merchant_category).lower() or "investment" in str(merchant_category).lower():
        reasons.append("Finance/Investment category is often targeted by fraud attempts.")

    if prob >= 0.70:
        reasons.append("Multiple risk signals combined pushed confidence high.")
    elif prob >= 0.35:
        reasons.append("Some risk signals exist, but not strong enough for high risk.")
    else:
        reasons.append("Most signals look normal, so confidence is low.")

    return reasons


# ---------- Dashboard helpers ----------
def dashboard_kpis(df: pd.DataFrame) -> dict[str, Any]:
    total = int(len(df))
    fraud = int((df["is_fraud"] == 1).sum())
    fraud_rate = round((fraud / total) * 100, 2) if total else 0.0
    avg_amount = format_inr(df["amount"].mean() if total else 0)
    return {
        "total_txn": total,
        "fraud_txn": fraud,
        "fraud_rate": fraud_rate,
        "avg_amount": avg_amount,
    }


def top_group_stats(df: pd.DataFrame, col: str, top_n: int = 6) -> list[dict[str, Any]]:
    g = df.groupby(col).agg(
        count=("is_fraud", "size"),
        fraud=("is_fraud", "sum"),
    ).reset_index()
    g["fraud_rate"] = (g["fraud"] / g["count"] * 100).round(2)
    g = g.sort_values("count", ascending=False).head(top_n)

    return [
        {"name": str(r[col]), "count": int(r["count"]), "fraud_rate": float(r["fraud_rate"])}
        for _, r in g.iterrows()
    ]


def day_night_breakdown(df: pd.DataFrame) -> dict[str, Any]:
    g = df.groupby("transaction_time").agg(
        total=("is_fraud", "size"),
        fraud=("is_fraud", "sum"),
    ).reset_index()
    g["safe"] = g["total"] - g["fraud"]

    order = ["Day", "Night"]
    g_map = {str(r["transaction_time"]): r for _, r in g.iterrows()}

    labels, safe_vals, fraud_vals = [], [], []
    for k in order:
        r = g_map.get(k, {"safe": 0, "fraud": 0})
        labels.append(k)
        safe_vals.append(int(r["safe"]))
        fraud_vals.append(int(r["fraud"]))

    return {"labels": labels, "safe": safe_vals, "fraud": fraud_vals}


def recent_rows_table(df: pd.DataFrame, n: int = 12) -> list[dict[str, Any]]:
    tail = df.tail(n).copy()
    out: list[dict[str, Any]] = []
    for _, r in tail.iterrows():
        out.append({
            "txn_id": int(r["txn_id"]),
            "amount": format_inr(r["amount"]),
            "payment_method": str(r["payment_method"]),
            "merchant_category": str(r["merchant_category"]),
            "transaction_time": str(r["transaction_time"]),
            "device_new": int(r["device_new"]),
            "location_change": int(r["location_change"]),
            "is_fraud": int(r["is_fraud"]),
        })
    return out


def build_alerts(df: pd.DataFrame) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    # Alert 1: extreme high amount fraud (top 1% amounts)
    high_amount = df["amount"].quantile(0.99)
    suspicious = df[(df["amount"] >= high_amount) & (df["is_fraud"] == 1)].head(2)
    for _, r in suspicious.iterrows():
        alerts.append({
            "title": "High amount + Fraud flagged",
            "desc": f"Txn #{int(r['txn_id'])} amount ₹{format_inr(r['amount'])} marked as fraud.",
            "hint": "Rule: top 1% amount + is_fraud=1",
        })

    # Alert 2: new device + fraud
    dev = df[(df["device_new"] == 1) & (df["is_fraud"] == 1)].head(2)
    for _, r in dev.iterrows():
        alerts.append({
            "title": "New device fraud signal",
            "desc": f"Txn #{int(r['txn_id'])} used a new device and was flagged fraud.",
            "hint": "Rule: device_new=1 + is_fraud=1",
        })

    return alerts[:4]


# ---------- Routes ----------
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = get_current_user()
    df = load_df()

    kpi = dashboard_kpis(df)
    device_new_pct = round((df["device_new"].mean() * 100), 2)
    location_change_pct = round((df["location_change"].mean() * 100), 2)

    by_method = top_group_stats(df, "payment_method", top_n=6)
    by_category = top_group_stats(df, "merchant_category", top_n=6)

    charts = {"dayNight": day_night_breakdown(df)}
    alerts = build_alerts(df)
    recent_rows = recent_rows_table(df, n=12)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "kpi": kpi,
            "device_new_pct": device_new_pct,
            "location_change_pct": location_change_pct,
            "by_method": by_method,
            "by_category": by_category,
            "recent_rows": recent_rows,
            "charts": charts,
            "alerts": alerts,
            "csv_path": str(CSV_PATH),
        },
    )


@router.get("/check", response_class=HTMLResponse)
def check_page(request: Request):
    user = get_current_user()
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@router.post("/predict", response_class=HTMLResponse)
def predict_page(
    request: Request,
    amount_raw: str = Form(...),
    payment_method: str = Form(...),
    merchant_category: str = Form(...),
    device_new: int = Form(...),
    location_change: int = Form(...),
    transaction_time: str = Form(...),
):
    user = get_current_user()

    amount = float(str(amount_raw).replace(",", "").strip() or 0)

    txn = {
        "amount": amount,
        "payment_method": payment_method,
        "merchant_category": merchant_category,
        "device_new": int(device_new),
        "location_change": int(location_change),
        "transaction_time": transaction_time,
    }

    pred = predict_one(txn)
    fraud_probability = float(pred["fraud_probability"])
    is_fraud = bool(pred["is_fraud"])

    risk_level = compute_risk_level(fraud_probability)
    reasons = build_reasons(
        fraud_probability,
        amount,
        int(device_new),
        int(location_change),
        transaction_time,
        payment_method,
        merchant_category,
    )

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "user": user,
            "fraud_probability": fraud_probability,
            "is_fraud": is_fraud,
            "risk_level": risk_level,
            "reasons": reasons,
            "amount_display": format_inr(amount),
            "payment_method": payment_method,
            "merchant_category": merchant_category,
            "device_label": "New Device 🆕" if int(device_new) == 1 else "Same Device ✅",
            "location_label": "Different Location 🧭" if int(location_change) == 1 else "Same Location 📍",
            "transaction_time": transaction_time,
        },
    )