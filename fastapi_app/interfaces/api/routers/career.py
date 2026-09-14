"""
Twentieth FastAPI slice: career center job listings, READ-ONLY. Mirrors
karyera_routes.py's career_center_page() route (open job listings plus
the viewer's own application status), including its MAXSUS/hacker-plan
gate. Posting jobs and applying stay on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.career.list_jobs import NotHackerPlanError, list_open_jobs
from fastapi_app.infrastructure.db.repositories.career_repository import SqlAlchemyCareerRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.career import JobListingResponse

router = APIRouter(prefix="/api/v2/career", tags=["career"])


@router.get("", response_model=list[JobListingResponse])
def career(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyCareerRepository(db)
    try:
        return [JobListingResponse(**j.__dict__) for j in list_open_jobs(repo, user_id)]
    except NotHackerPlanError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.")
