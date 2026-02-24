import os
from typing import Optional, Dict
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

COOKIE_NAME = "remember_token"
# Change this in production (or set APP_SECRET_KEY env var)
SECRET_KEY = os.getenv("APP_SECRET_KEY", "CHANGE_THIS_SECRET_KEY")
SALT = "opf-remember-token-v1"

serializer = URLSafeTimedSerializer(SECRET_KEY, salt=SALT)

def make_token(payload: Dict[str, str]) -> str:
    # payload should contain: username, role
    return serializer.dumps(payload)

def read_token(token: str, max_age_seconds: int) -> Optional[Dict[str, str]]:
    try:
        data = serializer.loads(token, max_age=max_age_seconds)
        if not isinstance(data, dict):
            return None
        username = str(data.get("username", "")).strip().lower()
        role = str(data.get("role", "user")).strip().lower()
        if not username:
            return None
        if role not in ("admin", "user"):
            role = "user"
        return {"username": username, "role": role}
    except (BadSignature, SignatureExpired):
        return None
