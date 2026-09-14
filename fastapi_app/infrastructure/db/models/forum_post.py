from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class ForumPostModel(Base):
    __tablename__ = "forum_posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text)
    views: Mapped[int] = mapped_column(BigInteger)
    replies_count: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[str] = mapped_column(Text)
