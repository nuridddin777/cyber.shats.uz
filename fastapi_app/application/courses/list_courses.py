from fastapi_app.domain.courses.entities import Course, Direction
from fastapi_app.domain.courses.repository import CoursesRepository


def list_courses_for_user(
    repo: CoursesRepository,
    user_id: int,
    direction_slug: str | None,
    search: str | None,
    level: str | None,
    limit: int = 60,
) -> tuple[list[Course], list[Direction]]:
    """Mirrors courses_routes.py's courses() route exactly: a student with a
    chosen primary direction is LOCKED to that direction's courses (plus any
    course they're already enrolled in, e.g. via an access code) — any `d`
    query param is ignored in that case. Non-students, and students with no
    chosen direction yet, browse freely."""
    role, primary_direction_id = repo.get_user_access(user_id)

    locked_direction: Direction | None = None
    also_include_course_ids: set[int] | None = None
    if role == "student" and primary_direction_id:
        locked_direction = repo.get_direction_by_id(primary_direction_id)
        if locked_direction:
            direction_slug = locked_direction.slug
            also_include_course_ids = repo.get_enrolled_course_ids(user_id)

    courses = repo.list_courses(direction_slug, also_include_course_ids, search, level, limit)
    directions = [locked_direction] if locked_direction else repo.list_active_directions()
    return courses, directions
