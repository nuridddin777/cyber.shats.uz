from typing import Protocol

from fastapi_app.domain.incubator.entities import IncubatorIdea


class IncubatorRepository(Protocol):
    def list_ideas(self, viewer_user_id: int) -> list[IncubatorIdea]: ...
    def get_user_plan(self, user_id: int) -> str | None: ...
