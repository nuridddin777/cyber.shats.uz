"""
Twenty-first FastAPI slice: startup incubator ideas board, READ-ONLY.
Mirrors inkubator_routes.py's incubator_page() route (ideas ranked by
vote count, plus the viewer's own vote status), including its MAXSUS/
hacker-plan gate. Posting ideas and voting stay on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.incubator.list_ideas import NotHackerPlanError, list_ideas
from fastapi_app.infrastructure.db.repositories.incubator_repository import SqlAlchemyIncubatorRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.incubator import IncubatorIdeaResponse

router = APIRouter(prefix="/api/v2/incubator", tags=["incubator"])


@router.get("", response_model=list[IncubatorIdeaResponse])
def incubator(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyIncubatorRepository(db)
    try:
        return [IncubatorIdeaResponse(**i.__dict__) for i in list_ideas(repo, user_id)]
    except NotHackerPlanError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.")
