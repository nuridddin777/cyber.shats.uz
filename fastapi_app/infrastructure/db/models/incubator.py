from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class IncubatorIdeaModel(Base):
    __tablename__ = "incubator_ideas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    stage: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)


class IncubatorVoteModel(Base):
    __tablename__ = "incubator_votes"

    idea_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
