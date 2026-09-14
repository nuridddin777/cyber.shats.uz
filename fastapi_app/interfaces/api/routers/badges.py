"""
Eleventh FastAPI slice: all badges plus which ones this user has earned,
READ-ONLY. Mirrors the queries used in app.py's results()/profile()/
leaderboard() routes. Badge-awarding logic stays wherever it currently
lives (award_xp/gamification triggers).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.badges.list_for_user import list_for_user
from fastapi_app.infrastructure.db.repositories.badges_repository import SqlAlchemyBadgesRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.badges import BadgeResponse

router = APIRouter(prefix="/api/v2/badges", tags=["badges"])


@router.get("", response_model=list[BadgeResponse])
def my_badges(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyBadgesRepository(db)
    return [BadgeResponse(**b.__dict__) for b in list_for_user(repo, user_id)]
