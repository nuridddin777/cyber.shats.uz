"""
Nineteenth FastAPI slice: freelance gig board, READ-ONLY. Mirrors
freelance_routes.py's freelance_page() route, including its MAXSUS/
hacker-plan gate. Creating gigs and responding stay on Flask.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.freelance.list_gigs import NotHackerPlanError, list_open_gigs
from fastapi_app.infrastructure.db.repositories.freelance_repository import SqlAlchemyFreelanceRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.freelance import FreelanceGigResponse

router = APIRouter(prefix="/api/v2/freelance", tags=["freelance"])


@router.get("", response_model=list[FreelanceGigResponse])
def freelance(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyFreelanceRepository(db)
    try:
        return [FreelanceGigResponse(**g.__dict__) for g in list_open_gigs(repo, user_id)]
    except NotHackerPlanError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.")
