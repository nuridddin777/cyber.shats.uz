from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.library.entities import Book, NewsItem
from fastapi_app.infrastructure.db.models.library import BookModel, NewsModel


class SqlAlchemyLibraryRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_books(self, category: str | None) -> list[Book]:
        query = select(BookModel)
        if category:
            query = query.where(BookModel.category == category)
        query = query.order_by(BookModel.id.desc())
        rows = self._db.execute(query).scalars().all()
        return [
            Book(id=b.id, title=b.title, type=b.type, size_label=b.size_label,
                 category=b.category, file_url=b.file_url)
            for b in rows
        ]

    def list_news(self, category: str | None, limit: int = 40) -> list[NewsItem]:
        query = select(NewsModel)
        if category:
            query = query.where(NewsModel.category == category)
        query = query.order_by(NewsModel.published_at.desc()).limit(limit)
        rows = self._db.execute(query).scalars().all()
        return [
            NewsItem(id=n.id, title=n.title, summary=n.summary, source=n.source,
                     category=n.category, published_at=n.published_at, url=n.url)
            for n in rows
        ]
