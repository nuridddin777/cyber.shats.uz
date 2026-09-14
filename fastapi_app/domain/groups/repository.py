from typing import Protocol

from fastapi_app.domain.groups.entities import Group


class GroupsRepository(Protocol):
    def list_all(self, viewer_user_id: int, limit: int) -> list[Group]: ...
