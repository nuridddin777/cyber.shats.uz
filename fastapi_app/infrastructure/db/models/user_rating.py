from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class UserRatingModel(Base):
    __tablename__ = "user_ratings"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    total_score: Mapped[int] = mapped_column(BigInteger)
    courses_done: Mapped[int] = mapped_column(BigInteger)
    rank_position: Mapped[int] = mapped_column(BigInteger)
