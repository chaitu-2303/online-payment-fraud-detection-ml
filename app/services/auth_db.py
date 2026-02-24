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
    conn.commit()
    conn.close()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "created_at": row["created_at"],
        "last_login": row["last_login"],
    }


def _total_users() -> int:
    init_db()
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    init_db()
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


def get_user_public(username: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_username(username)
    if not user:
        return None
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "created_at": user["created_at"],
        "last_login": user["last_login"],
    }


def list_users() -> List[Dict[str, Any]]:
    init_db()
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, username, role, created_at, last_login FROM users ORDER BY id ASC"
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def count_admins() -> int:
    init_db()
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE LOWER(role) = 'admin'"
    ).fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def set_user_role(username: str, new_role: str) -> bool:
    init_db()
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
    init_db()
    username = username.strip().lower()
    conn = get_conn()
    conn.execute(
        "UPDATE users SET last_login = ? WHERE username = ?",
        (_utc_now_iso(), username),
    )
    conn.commit()
    conn.close()


def create_user(username: str, password: str) -> bool:
    init_db()
    username = username.strip().lower()

    # Limit password to 72 bytes when encoded as UTF-8, then decode safely
    password_limited = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
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
    init_db()
    username = username.strip().lower()

    conn = get_conn()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()

    if not row:
        return False

    # Apply the same UTF-8 72-byte limit before verification
    password_limited = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    try:
        return pwd_context.verify(password_limited, row["password_hash"])
    except Exception:
        return False
