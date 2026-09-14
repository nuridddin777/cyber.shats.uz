"""
Twenty-third FastAPI slice: SHATS LIVE stream schedule, READ-ONLY.
Mirrors shatslive_routes.py's shats_live_page() route (live streams
first, then by scheduled time), including its MAXSUS/hacker-plan gate.
Scheduling, going live, and ending a stream stay on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.shatslive.list_streams import NotHackerPlanError, list_streams
from fastapi_app.infrastructure.db.repositories.shatslive_repository import SqlAlchemyShatsLiveRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.shatslive import LiveStreamResponse

router = APIRouter(prefix="/api/v2/shats-live", tags=["shats-live"])


@router.get("", response_model=list[LiveStreamResponse])
def shats_live(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyShatsLiveRepository(db)
    try:
        return [LiveStreamResponse(**s.__dict__) for s in list_streams(repo, user_id)]
    except NotHackerPlanError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.")
