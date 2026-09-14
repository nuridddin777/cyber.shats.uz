"""
Tenth FastAPI slice: a user's own course enrollments, READ-ONLY. Mirrors
the query used in app.py's results() route. Enrolling itself (spending
coins to buy a course) stays in coins.py/app.py.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.enrollments.list_for_user import list_for_user
from fastapi_app.infrastructure.db.repositories.enrollments_repository import SqlAlchemyEnrollmentsRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.enrollments import EnrollmentResponse

router = APIRouter(prefix="/api/v2/enrollments", tags=["enrollments"])


@router.get("", response_model=list[EnrollmentResponse])
def my_enrollments(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyEnrollmentsRepository(db)
    return [EnrollmentResponse(**e.__dict__) for e in list_for_user(repo, user_id)]
