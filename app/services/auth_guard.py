from fastapi import Request
from fastapi.responses import RedirectResponse
from typing import Optional, Dict

from app.services.auth_tokens import COOKIE_NAME, read_token

REMEMBER_MAX_AGE = 60 * 60 * 24 * 30  # 30 days

def get_current_user(request: Request) -> Optional[Dict[str, str]]:
    # 1) session
    if request.session.get("user"):
        role = request.session.get("role", "user")
        if role not in ("admin", "user"):
            role = "user"
        return {"username": request.session["user"], "role": role}

    # 2) remember-me cookie
    token = request.cookies.get(COOKIE_NAME)
    if token:
        data = read_token(token, max_age_seconds=REMEMBER_MAX_AGE)
        if data:
            request.session["user"] = data["username"]
            request.session["role"] = data["role"]
            return data

    return None

def require_login(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return None

def require_admin(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if user["role"] != "admin":
        return RedirectResponse(url="/", status_code=303)
    return None
