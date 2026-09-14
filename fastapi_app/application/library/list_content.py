from fastapi_app.domain.library.entities import Book, NewsItem
from fastapi_app.domain.library.repository import LibraryRepository


def list_books(repo: LibraryRepository, category: str | None) -> list[Book]:
    return repo.list_books(category)


def list_news(repo: LibraryRepository, category: str | None, limit: int = 40) -> list[NewsItem]:
    return repo.list_news(category, limit)
