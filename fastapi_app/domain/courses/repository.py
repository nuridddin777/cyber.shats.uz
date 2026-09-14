from typing import Protocol

from fastapi_app.domain.courses.entities import Course, Direction


class CoursesRepository(Protocol):
    def get_user_access(self, user_id: int) -> tuple[str, int | None]:
        """Returns (role, primary_direction_id)."""
        ...

    def get_direction_by_id(self, direction_id: int) -> Direction | None: ...
    def list_active_directions(self) -> list[Direction]: ...
    def get_enrolled_course_ids(self, user_id: int) -> set[int]: ...

    def list_courses(
        self,
        direction_slug: str | None,
        also_include_course_ids: set[int] | None,
        search: str | None,
        level: str | None,
        limit: int,
    ) -> list[Course]: ...
