from fastapi_app.domain.forum.entities import ForumCategory, ForumPost
from fastapi_app.domain.forum.repository import ForumRepository


def list_posts(repo: ForumRepository, category: str | None, limit: int = 50) -> list[ForumPost]:
    return repo.list_posts(category, limit)


def list_categories(repo: ForumRepository) -> list[ForumCategory]:
    return repo.list_categories()
