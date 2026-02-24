from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.services.auth_guard import get_current_user, require_admin
from app.services.auth_db import list_users, set_user_role, count_admins

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, msg: str | None = None, err: str | None = None):
    redir = require_admin(request)
    if redir:
        return redir

    me = get_current_user(request)
    users = list_users()

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "user": me,
            "users": users,
            "msg": msg,
            "err": err,
            "admin_count": count_admins(),
        },
    )

@router.post("/admin/role")
def admin_set_role(request: Request, username: str = Form(...), role: str = Form(...)):
    redir = require_admin(request)
    if redir:
        return redir

    me = get_current_user(request)
    username = username.strip().lower()

    if me and username == me["username"]:
        return RedirectResponse(url="/admin?err=You+can%27t+change+your+own+role+from+the+dashboard.", status_code=303)

    ok = set_user_role(username, role)
    if not ok:
        return RedirectResponse(url="/admin?err=Failed+to+update+role", status_code=303)

    return RedirectResponse(url="/admin?msg=Role+updated", status_code=303)
