from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.courses.entities import Course, Direction
from fastapi_app.infrastructure.db.models.course import CourseModel, DirectionModel
from fastapi_app.infrastructure.db.models.enrollment import EnrollmentModel
from fastapi_app.infrastructure.db.models.user import UserModel


def _to_direction(d: DirectionModel) -> Direction:
    return Direction(id=d.id, slug=d.slug, name_uz=d.name_uz, icon=d.icon,
                      description=d.description, color=d.color)


class SqlAlchemyCoursesRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_user_access(self, user_id: int) -> tuple[str, int | None]:
        row = self._db.execute(
            select(UserModel.role, UserModel.primary_direction_id).where(UserModel.id == user_id)
        ).first()
        if not row:
            return "student", None
        return row.role, row.primary_direction_id

    def get_direction_by_id(self, direction_id: int) -> Direction | None:
        d = self._db.get(DirectionModel, direction_id)
        return _to_direction(d) if d else None

    def list_active_directions(self) -> list[Direction]:
        rows = self._db.execute(
            select(DirectionModel).where(DirectionModel.is_active == 1).order_by(DirectionModel.sort_order)
        ).scalars().all()
        return [_to_direction(d) for d in rows]

    def get_enrolled_course_ids(self, user_id: int) -> set[int]:
        rows = self._db.execute(
            select(EnrollmentModel.course_id).where(EnrollmentModel.user_id == user_id)
        ).scalars().all()
        return set(rows)

    def list_courses(
        self,
        direction_slug: str | None,
        also_include_course_ids: set[int] | None,
        search: str | None,
        level: str | None,
        limit: int,
    ) -> list[Course]:
        query = (
            select(CourseModel, DirectionModel.name_uz, DirectionModel.slug)
            .join(DirectionModel, DirectionModel.id == CourseModel.direction_id)
            .where(CourseModel.is_active == 1)
        )
        if direction_slug and also_include_course_ids:
            query = query.where(
                (DirectionModel.slug == direction_slug) | (CourseModel.id.in_(also_include_course_ids))
            )
        elif direction_slug:
            query = query.where(DirectionModel.slug == direction_slug)
        if search:
            query = query.where(CourseModel.title.ilike(f"%{search}%"))
        if level:
            query = query.where(CourseModel.level == level)
        query = query.order_by(CourseModel.students_count.desc()).limit(limit)

        rows = self._db.execute(query).all()
        return [
            Course(
                id=c.id, slug=c.slug, title=c.title, subtitle=c.subtitle, description=c.description,
                level=c.level, duration_weeks=c.duration_weeks, lessons_count=c.lessons_count,
                students_count=c.students_count, rating=c.rating, price=c.price, icon=c.icon,
                code_price=c.code_price, is_pro_only=c.is_pro_only, is_paid=c.is_paid,
                direction_id=c.direction_id, direction_name=d_name, direction_slug=d_slug,
            )
            for c, d_name, d_slug in rows
        ]
