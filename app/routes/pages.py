from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.routes.auth import get_current_user
from app.services.inference import predict_one, get_model_metrics
from app.services.auth_db import save_prediction, get_user_predictions, get_prediction_stats

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

BASE_DIR = Path(__file__).resolve().parents[2]
CSV_PATH = BASE_DIR / "data" / "fraud_data.csv"

_cached_df: pd.DataFrame | None = None


def _require_login(request: Request):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse(url="/login", status_code=303)
    return user, None


def load_df() -> pd.DataFrame:
    global _cached_df
    if _cached_df is None:
        if not CSV_PATH.exists():
            raise FileNotFoundError(f"CSV not found at: {CSV_PATH}")
        _cached_df = pd.read_csv(CSV_PATH)
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
    device_type: str,
    device_change: int,
    location: str,
    is_international: int,
    transaction_time: int,
    transaction_frequency: int,
    failed_transactions_24h: int,
    account_age_days: int,
    avg_transaction_amount: float,
) -> list[str]:
    reasons: list[str] = []

    if amount >= 15000:
        reasons.append("High transaction amount increases risk significantly.")
    elif amount >= 5000:
        reasons.append("Moderately high amount — could be suspicious depending on behavior.")
    else:
        reasons.append("Transaction amount appears normal for regular spending.")

    if device_change == 1:
        reasons.append("Transaction made from a different device than usual.")
    else:
        reasons.append("Same device used as previous transactions — lower risk.")

    if is_international == 1:
        reasons.append("International transaction detected — higher risk profile.")

    if transaction_time >= 22 or transaction_time <= 4:
        reasons.append("Late-night transaction (high-risk time window).")
    elif transaction_time >= 6 and transaction_time <= 20:
        reasons.append("Transaction during normal business hours.")

    if failed_transactions_24h >= 3:
        reasons.append(f"{failed_transactions_24h} failed transactions in 24h — unusual pattern.")
    elif failed_transactions_24h >= 1:
        reasons.append("Some recent failed transactions — worth monitoring.")

    if transaction_frequency >= 30:
        reasons.append("Very high transaction frequency — potential automated activity.")

    if account_age_days < 30:
        reasons.append("New account (less than 30 days old) — higher risk.")
    elif account_age_days > 365:
        reasons.append("Established account with long history — lower risk.")

    if amount > 0 and avg_transaction_amount > 0:
        ratio = amount / avg_transaction_amount
        if ratio >= 5:
            reasons.append(f"Amount is {ratio:.1f}x the user's average — significant deviation.")
        elif ratio >= 2:
            reasons.append(f"Amount is {ratio:.1f}x the user's average — slightly unusual.")

    if location in ("rural",):
        reasons.append("Transaction from rural area — less common for online payments.")

    if prob >= 0.70:
        reasons.append("Multiple high-risk signals combined — strong fraud indicators.")
    elif prob >= 0.40:
        reasons.append("Some risk signals present but not conclusive.")
    else:
        reasons.append("Most signals appear normal — low fraud confidence.")

    return reasons


def dashboard_kpis(df: pd.DataFrame) -> dict[str, Any]:
    total = int(len(df))
    fraud = int((df["is_fraud"] == 1).sum())
    fraud_rate = round((fraud / total) * 100, 2) if total else 0.0
    avg_amount = format_inr(df["amount"].mean() if total else 0)
    return {
        "total_txn": f"{total:,}",
        "fraud_txn": f"{fraud:,}",
        "fraud_rate": fraud_rate,
        "avg_amount": avg_amount,
    }


def top_group_stats(df: pd.DataFrame, col: str, top_n: int = 6) -> list[dict[str, Any]]:
    g = (
        df.groupby(col)
        .agg(count=("is_fraud", "size"), fraud=("is_fraud", "sum"))
        .reset_index()
    )
    g["fraud_rate"] = (g["fraud"] / g["count"] * 100).round(2)
    g = g.sort_values("count", ascending=False).head(top_n)
    return [
        {"name": str(r[col]), "count": int(r["count"]), "fraud_rate": float(r["fraud_rate"])}
        for _, r in g.iterrows()
    ]


def time_distribution(df: pd.DataFrame) -> dict[str, Any]:
    bins = [0, 6, 12, 18, 24]
    labels_map = ["Night (0-6)", "Morning (6-12)", "Afternoon (12-18)", "Evening (18-24)"]
    df_copy = df.copy()
    df_copy["time_slot"] = pd.cut(df_copy["transaction_time"], bins=bins, labels=labels_map, right=False, include_lowest=True)
    g = df_copy.groupby("time_slot", observed=False).agg(
        total=("is_fraud", "size"), fraud=("is_fraud", "sum")
    ).reset_index()
    g["safe"] = g["total"] - g["fraud"]
    return {
        "labels": g["time_slot"].tolist(),
        "safe": g["safe"].tolist(),
        "fraud": g["fraud"].tolist(),
    }


def recent_rows_table(df: pd.DataFrame, n: int = 12) -> list[dict[str, Any]]:
    tail = df.tail(n).copy()
    out: list[dict[str, Any]] = []
    for _, r in tail.iterrows():
        out.append(
            {
                "txn_id": int(r.get("transaction_id", 0)),
                "amount": format_inr(r["amount"]),
                "payment_method": str(r["payment_method"]),
                "merchant_category": str(r["merchant_category"]),
                "device_type": str(r["device_type"]),
                "location": str(r["location"]),
                "transaction_time": int(r["transaction_time"]),
                "is_fraud": int(r["is_fraud"]),
            }
        )
    return out


def build_alerts(df: pd.DataFrame) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    high_amount = df["amount"].quantile(0.99)
    suspicious = df[(df["amount"] >= high_amount) & (df["is_fraud"] == 1)].head(2)
    for _, r in suspicious.iterrows():
        alerts.append(
            {
                "title": "High-value fraud detected",
                "desc": f"Transaction #{int(r.get('transaction_id', 0))} — ₹{format_inr(r['amount'])} flagged as fraud.",
                "level": "danger",
            }
        )
    dev = df[(df["device_change"] == 1) & (df["is_fraud"] == 1)].head(2)
    for _, r in dev.iterrows():
        alerts.append(
            {
                "title": "Device change fraud",
                "desc": f"Transaction #{int(r.get('transaction_id', 0))} — device changed and flagged fraud.",
                "level": "warning",
            }
        )
    intl = df[(df["is_international"] == 1) & (df["is_fraud"] == 1)].head(1)
    for _, r in intl.iterrows():
        alerts.append(
            {
                "title": "International fraud signal",
                "desc": f"Transaction #{int(r.get('transaction_id', 0))} — international payment flagged.",
                "level": "warning",
            }
        )
    return alerts[:5]


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user, redir = _require_login(request)
    if redir:
        return redir

    df = load_df()
    kpi = dashboard_kpis(df)

    intl_pct = round((df["is_international"].mean() * 100), 2)
    device_change_pct = round((df["device_change"].mean() * 100), 2)

    by_method = top_group_stats(df, "payment_method", top_n=6)
    by_category = top_group_stats(df, "merchant_category", top_n=6)

    charts = {"timeDistribution": time_distribution(df)}
    alerts = build_alerts(df)
    recent_rows = recent_rows_table(df, n=12)

    pred_stats = get_prediction_stats(user["username"])
    model_info = get_model_metrics()

    return templates.TemplateResponse(
        request, "dashboard.html",
        context={
            "user": user,
            "kpi": kpi,
            "intl_pct": intl_pct,
            "device_change_pct": device_change_pct,
            "by_method": by_method,
            "by_category": by_category,
            "recent_rows": recent_rows,
            "charts": charts,
            "alerts": alerts,
            "pred_stats": pred_stats,
            "model_info": model_info,
            "active_page": "dashboard",
        },
    )


@router.get("/check", response_class=HTMLResponse)
def check_page(request: Request):
    user, redir = _require_login(request)
    if redir:
        return redir
    return templates.TemplateResponse(
        request, "index.html", context={"user": user, "active_page": "check"}
    )


@router.post("/predict", response_class=HTMLResponse)
def predict_page(
    request: Request,
    amount: str = Form(...),
    payment_method: str = Form(...),
    merchant_category: str = Form(...),
    device_type: str = Form(...),
    location: str = Form(...),
    transaction_time: int = Form(...),
    transaction_frequency: int = Form(5),
    account_age_days: int = Form(365),
    avg_transaction_amount: str = Form("0"),
    failed_transactions_24h: int = Form(0),
    is_international: int = Form(0),
    device_change: int = Form(0),
):
    user, redir = _require_login(request)
    if redir:
        return redir

    amount_val = float(str(amount).replace(",", "").strip() or 0)
    avg_txn_val = float(str(avg_transaction_amount).replace(",", "").strip() or 0)

    txn = {
        "amount": amount_val,
        "payment_method": payment_method,
        "merchant_category": merchant_category,
        "device_type": device_type,
        "location": location,
        "transaction_time": transaction_time,
        "transaction_frequency": transaction_frequency,
        "account_age_days": account_age_days,
        "avg_transaction_amount": avg_txn_val,
        "failed_transactions_24h": failed_transactions_24h,
        "is_international": is_international,
        "device_change": device_change,
    }

    pred = predict_one(txn)
    fraud_probability = float(pred["fraud_probability"])
    is_fraud = bool(pred["is_fraud"])
    risk_level = compute_risk_level(fraud_probability)

    result = {
        "fraud_probability": fraud_probability,
        "is_fraud": is_fraud,
        "risk_level": risk_level,
    }
    save_prediction(user["username"], txn, result)

    reasons = build_reasons(
        fraud_probability,
        amount_val,
        device_type,
        device_change,
        location,
        is_international,
        transaction_time,
        transaction_frequency,
        failed_transactions_24h,
        account_age_days,
        avg_txn_val,
    )

    return templates.TemplateResponse(
        request, "result.html",
        context={
            "user": user,
            "fraud_probability": fraud_probability,
            "is_fraud": is_fraud,
            "risk_level": risk_level,
            "reasons": reasons,
            "amount_display": format_inr(amount_val),
            "payment_method": payment_method,
            "merchant_category": merchant_category,
            "device_type": device_type,
            "location": location,
            "transaction_time": transaction_time,
            "transaction_frequency": transaction_frequency,
            "account_age_days": account_age_days,
            "avg_transaction_amount": format_inr(avg_txn_val),
            "failed_transactions_24h": failed_transactions_24h,
            "is_international": is_international,
            "device_change": device_change,
            "active_page": "check",
        },
    )


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    user, redir = _require_login(request)
    if redir:
        return redir

    predictions = get_user_predictions(user["username"], limit=50)
    pred_stats = get_prediction_stats(user["username"])

    return templates.TemplateResponse(
        request, "history.html",
        context={
            "user": user,
            "predictions": predictions,
            "pred_stats": pred_stats,
            "active_page": "history",
        },
    )