from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class BadgeModel(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)


class UserBadgeModel(Base):
    __tablename__ = "user_badges"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    badge_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    earned_at: Mapped[str] = mapped_column(Text)
