import base64
import hmac
import hashlib
import time
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.auth_db import (
    create_user,
    verify_user,
    get_user_by_username,
    list_users,
    set_user_role,
    count_admins,
    update_last_login,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

REMEMBER_COOKIE_NAME = "remember_token"
REMEMBER_MAX_AGE_SECONDS = 30 * 24 * 60 * 60


def _app_secret(request: Request) -> str:
    return getattr(request.app.state, "secret_key", "CHANGE_THIS_SECRET_KEY")


def _sign_remember(secret: str, username: str, exp: int) -> str:
    msg = f"{username}|{exp}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    raw = f"{username}|{exp}|{sig}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _verify_remember(secret: str, token: str) -> Optional[str]:
    try:
        raw = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        username, exp_str, sig = raw.split("|", 2)
        exp = int(exp_str)

        if exp < int(time.time()):
            return None

        msg = f"{username}|{exp}".encode("utf-8")
        expected_sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

        if not hmac.compare_digest(sig, expected_sig):
            return None

        return username
    except Exception:
        return None


def _restore_session_from_remember(request: Request) -> None:
    if request.session.get("user"):
        return

    token = request.cookies.get(REMEMBER_COOKIE_NAME)
    if not token:
        return

    username = _verify_remember(_app_secret(request), token)
    if not username:
        return

    user = get_user_by_username(username)
    if not user:
        return

    request.session["user"] = username


def _password_too_long(password: str) -> bool:
    """Return True if the password's UTF-8 encoding exceeds 72 bytes.

    Bcrypt has a 72-byte input limit; we enforce the same here to avoid
    truncation issues when hashing.
    """
    try:
        return len(password.encode("utf-8")) > 72
    except Exception:
        return True


def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    _restore_session_from_remember(request)
    username = request.session.get("user")
    if not username:
        return None
    return get_user_by_username(username)




@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: Optional[str] = Form(None),
):
    username = username.strip().lower()



    if verify_user(username, password):
        request.session["user"] = username
        update_last_login(username)

        resp = RedirectResponse(url="/", status_code=303)

        if remember_me:
            exp = int(time.time()) + REMEMBER_MAX_AGE_SECONDS
            token = _sign_remember(_app_secret(request), username, exp)
            resp.set_cookie(
                REMEMBER_COOKIE_NAME,
                token,
                max_age=REMEMBER_MAX_AGE_SECONDS,
                httponly=True,
                samesite="lax",
                secure=False,
            )
        else:
            resp.delete_cookie(REMEMBER_COOKIE_NAME)

        return resp

    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"},
    )


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    if get_current_user(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    username = username.strip().lower()

    if len(username) < 3:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Username must be at least 3 characters."},
        )

    if _password_too_long(password):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password too long (max 72 bytes)."},
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password must be at least 6 characters."},
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match."},
        )

    ok = create_user(username, password)
    if not ok:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Username already exists."},
        )

    return RedirectResponse(url="/login", status_code=303)


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(REMEMBER_COOKIE_NAME)
    return resp


@router.get("/profile", response_class=HTMLResponse)
def profile(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if (user.get("role") or "").lower() != "admin":
        return RedirectResponse(url="/", status_code=303)

    users: List[Dict[str, Any]] = list_users()
    return templates.TemplateResponse("admin.html", {"request": request, "admin": user, "users": users})


@router.post("/admin/role")
def admin_change_role(
    request: Request,
    target_username: str = Form(...),
    new_role: str = Form(...),
):
    admin = get_current_user(request)
    if not admin:
        return RedirectResponse(url="/login", status_code=303)

    if (admin.get("role") or "").lower() != "admin":
        return RedirectResponse(url="/", status_code=303)

    target_username = target_username.strip().lower()
    new_role = new_role.strip().lower()

    if new_role not in {"admin", "user"}:
        return RedirectResponse(url="/admin", status_code=303)

    if admin.get("username", "").lower() == target_username:
        return RedirectResponse(url="/admin", status_code=303)

    if new_role == "user":
        target = get_user_by_username(target_username)
        if target and (target.get("role") or "").lower() == "admin":
            if count_admins() <= 1:
                return RedirectResponse(url="/admin", status_code=303)

    set_user_role(target_username, new_role)
    return RedirectResponse(url="/admin", status_code=303)