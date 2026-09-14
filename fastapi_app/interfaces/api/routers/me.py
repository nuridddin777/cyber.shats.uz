"""
Second FastAPI slice: /api/v2/me. First one that needs to know who's
logged in — proves the shared Flask-session-cookie bridge (deps.py) and
the first real SQLAlchemy model (users) work together, read-only.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.users.get_profile import get_profile
from fastapi_app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.user import UserProfileResponse

router = APIRouter(prefix="/api/v2", tags=["me"])


@router.get("/me", response_model=UserProfileResponse)
def me(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyUserRepository(db)
    profile = get_profile(repo, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return UserProfileResponse(**profile.__dict__)
