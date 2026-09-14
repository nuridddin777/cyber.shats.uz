from typing import Protocol

from fastapi_app.domain.library.entities import Book, NewsItem


class LibraryRepository(Protocol):
    def list_books(self, category: str | None) -> list[Book]: ...
    def list_news(self, category: str | None, limit: int) -> list[NewsItem]: ...
