from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.enrollments.entities import Enrollment
from fastapi_app.infrastructure.db.models.enrollment import EnrollmentModel
from fastapi_app.infrastructure.db.models.course import CourseModel


class SqlAlchemyEnrollmentsRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_for_user(self, user_id: int) -> list[Enrollment]:
        rows = self._db.execute(
            select(EnrollmentModel, CourseModel.title, CourseModel.slug, CourseModel.icon)
            .join(CourseModel, CourseModel.id == EnrollmentModel.course_id)
            .where(EnrollmentModel.user_id == user_id)
            .order_by(EnrollmentModel.started_at.desc())
        ).all()
        return [
            Enrollment(
                id=e.id, course_id=e.course_id, title=title, slug=slug, icon=icon,
                progress_percent=e.progress_percent, started_at=e.started_at, completed_at=e.completed_at,
            )
            for e, title, slug, icon in rows
        ]
