from typing import Protocol

from fastapi_app.domain.mentors.entities import Mentor


class MentorsRepository(Protocol):
    def list_all(self) -> list[Mentor]: ...
    def get_user_plan(self, user_id: int) -> str | None: ...
