from fastapi import Request, HTTPException

from fastapi_app.infrastructure.legacy.flask_session import read_session_cookie
from fastapi_app.infrastructure.db.base import SessionLocal


def get_current_user_id(request: Request) -> int:
    """Identifies the logged-in user from the same cookie Flask set — no
    separate FastAPI-side login exists or is planned; auth stays Flask-owned."""
    cookie = request.cookies.get("session", "")
    data = read_session_cookie(cookie)
    user_id = data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Avtorizatsiya talab qilinadi")
    return user_id


def get_db_session():
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database sozlanmagan (DATABASE_URL yo'q)")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
