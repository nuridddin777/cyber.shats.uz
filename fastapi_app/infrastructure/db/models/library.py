from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class BookModel(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    size_label: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    file_url: Mapped[str] = mapped_column(Text)


class NewsModel(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    published_at: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
