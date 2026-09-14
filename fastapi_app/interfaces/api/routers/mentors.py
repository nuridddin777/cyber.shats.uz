"""
Eighteenth FastAPI slice: mentor directory, READ-ONLY. Mirrors
mentors_routes.py's mentors_page() route, including its "MAXSUS (hacker
plan)" gate (app.py's _require_hacker_plan()). Registering as a mentor and
requesting mentorship stay on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.mentors.list_mentors import NotHackerPlanError, list_mentors
from fastapi_app.infrastructure.db.repositories.mentors_repository import SqlAlchemyMentorsRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.mentors import MentorResponse

router = APIRouter(prefix="/api/v2/mentors", tags=["mentors"])


@router.get("", response_model=list[MentorResponse])
def mentors(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyMentorsRepository(db)
    try:
        return [MentorResponse(**m.__dict__) for m in list_mentors(repo, user_id)]
    except NotHackerPlanError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.")
