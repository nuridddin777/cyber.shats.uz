"""
Fourteenth FastAPI slice: course catalog, READ-ONLY. Mirrors
courses_routes.py's courses() route, including its access control: a
student with a chosen primary direction only sees that direction's
courses (plus anything they're already enrolled in); everyone else browses
freely. Enrolling, lesson content, and admin editing stay on Flask.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.application.courses.list_courses import list_courses_for_user
from fastapi_app.infrastructure.db.repositories.courses_repository import SqlAlchemyCoursesRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.courses import CourseResponse, CoursesListResponse, DirectionResponse

router = APIRouter(prefix="/api/v2/courses", tags=["courses"])


@router.get("", response_model=CoursesListResponse)
def courses(
    d: str | None = Query(default=None),
    q: str | None = Query(default=None),
    level: str | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyCoursesRepository(db)
    course_list, direction_list = list_courses_for_user(repo, user_id, d, q, level)
    return CoursesListResponse(
        courses=[CourseResponse(**c.__dict__) for c in course_list],
        directions=[DirectionResponse(**dd.__dict__) for dd in direction_list],
    )
