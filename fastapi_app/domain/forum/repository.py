from typing import Protocol

from fastapi_app.domain.forum.entities import ForumCategory, ForumPost


class ForumRepository(Protocol):
    def list_posts(self, category: str | None, limit: int) -> list[ForumPost]: ...
    def list_categories(self) -> list[ForumCategory]: ...
