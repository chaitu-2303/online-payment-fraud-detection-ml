import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

DB_PATH = os.path.join("app", "data", "users.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL,
            last_login TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            amount REAL,
            payment_method TEXT,
            merchant_category TEXT,
            device_type TEXT,
            location TEXT,
            transaction_frequency INTEGER,
            account_age_days INTEGER,
            avg_transaction_amount REAL,
            failed_transactions_24h INTEGER,
            is_international INTEGER,
            device_change INTEGER,
            transaction_hour INTEGER,
            fraud_probability REAL,
            is_fraud INTEGER,
            risk_level TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
        "last_login": row["last_login"],
    }


def _total_users() -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    username = username.strip().lower()
    conn = get_conn()
    row = conn.execute(
        "SELECT id, username, role, created_at, last_login FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_dict(row)


def list_users() -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, username, role, created_at, last_login FROM users ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def count_admins() -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE LOWER(role) = 'admin'"
    ).fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def set_user_role(username: str, new_role: str) -> bool:
    username = username.strip().lower()
    new_role = new_role.strip().lower()
    if new_role not in {"admin", "user"}:
        return False
    conn = get_conn()
    cur = conn.execute(
        "UPDATE users SET role = ? WHERE username = ?",
        (new_role, username),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def update_last_login(username: str) -> None:
    username = username.strip().lower()
    conn = get_conn()
    conn.execute(
        "UPDATE users SET last_login = ? WHERE username = ?",
        (_utc_now_iso(), username),
    )
    conn.commit()
    conn.close()


def create_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    password_limited = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    password_hash = pwd_context.hash(password_limited)
    created_at = _utc_now_iso()
    role = "admin" if _total_users() == 0 else "user"

    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at, last_login) VALUES (?, ?, ?, ?, ?)",
            (username, password_hash, role, created_at, None),
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username: str, password: str) -> bool:
    username = username.strip().lower()
    conn = get_conn()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if not row:
        return False

    password_limited = password.encode("utf-8")[:72].decode("utf-8", errors="ignore")
    try:
        return pwd_context.verify(password_limited, row["password_hash"])
    except Exception:
        return False


def save_prediction(username: str, txn: Dict[str, Any], result: Dict[str, Any]) -> int:
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO predictions
        (username, amount, payment_method, merchant_category, device_type,
         location, transaction_frequency, account_age_days, avg_transaction_amount,
         failed_transactions_24h, is_international, device_change, transaction_hour,
         fraud_probability, is_fraud, risk_level, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            username,
            txn.get("amount", 0),
            txn.get("payment_method", ""),
            txn.get("merchant_category", ""),
            txn.get("device_type", ""),
            txn.get("location", ""),
            txn.get("transaction_frequency", 0),
            txn.get("account_age_days", 0),
            txn.get("avg_transaction_amount", 0),
            txn.get("failed_transactions_24h", 0),
            txn.get("is_international", 0),
            txn.get("device_change", 0),
            txn.get("transaction_time", 0),
            result.get("fraud_probability", 0),
            1 if result.get("is_fraud") else 0,
            result.get("risk_level", "Low"),
            _utc_now_iso(),
        ),
    )
    conn.commit()
    pred_id = cur.lastrowid
    conn.close()
    return pred_id


def get_user_predictions(username: str, limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, amount, payment_method, merchant_category, device_type,
                  location, fraud_probability, is_fraud, risk_level, created_at
           FROM predictions WHERE username = ?
           ORDER BY id DESC LIMIT ?""",
        (username.strip().lower(), limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_prediction_stats(username: str = None) -> Dict[str, Any]:
    conn = get_conn()
    if username:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM predictions WHERE username = ?", (username,)
        ).fetchone()["c"]
        fraud = conn.execute(
            "SELECT COUNT(*) AS c FROM predictions WHERE username = ? AND is_fraud = 1",
            (username,),
        ).fetchone()["c"]
    else:
        total = conn.execute("SELECT COUNT(*) AS c FROM predictions").fetchone()["c"]
        fraud = conn.execute(
            "SELECT COUNT(*) AS c FROM predictions WHERE is_fraud = 1"
        ).fetchone()["c"]
    conn.close()
    return {
        "total_checks": total,
        "fraud_detected": fraud,
        "safe_detected": total - fraud,
        "fraud_rate": round((fraud / total * 100), 2) if total > 0 else 0,
    }
