from typing import Protocol

from fastapi_app.domain.badges.entities import Badge


class BadgesRepository(Protocol):
    def list_for_user(self, user_id: int) -> list[Badge]: ...
