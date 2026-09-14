"""
Thirteenth FastAPI slice: approved startups feed, READ-ONLY. Mirrors the
query used in startups_routes.py's startups_list() route (startups.py's
get_approved_startups()), plus per-viewer like status/count. Creating,
liking, bidding, and admin review stay on the legacy Flask side for now.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.application.startups.list_approved import list_approved
from fastapi_app.infrastructure.db.repositories.startups_repository import SqlAlchemyStartupsRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.startups import StartupResponse

router = APIRouter(prefix="/api/v2/startups", tags=["startups"])


@router.get("", response_model=list[StartupResponse])
def approved_startups(
    limit: int = Query(default=100, le=500),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyStartupsRepository(db)
    return [StartupResponse(**s.__dict__) for s in list_approved(repo, user_id, limit)]
