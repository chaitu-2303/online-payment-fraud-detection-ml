import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.routes.pages import router as pages_router
from app.routes.auth import router as auth_router

APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "CHANGE_THIS_SECRET_KEY")

app = FastAPI(title="PayShield AI — Online Payment Fraud Detection")
app.state.secret_key = APP_SECRET_KEY

app.add_middleware(SessionMiddleware, secret_key=APP_SECRET_KEY)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_router)
app.include_router(pages_router)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", reload=True)
