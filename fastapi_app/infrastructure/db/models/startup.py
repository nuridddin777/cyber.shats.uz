from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class StartupModel(Base):
    __tablename__ = "startups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    image_path: Mapped[str] = mapped_column(Text, nullable=True)
    link_url: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    view_count: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[str] = mapped_column(Text)
    in_auction: Mapped[int] = mapped_column(BigInteger)
    needs_help: Mapped[int] = mapped_column(BigInteger)


class StartupLikeModel(Base):
    __tablename__ = "startup_likes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    startup_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[str] = mapped_column(Text)
