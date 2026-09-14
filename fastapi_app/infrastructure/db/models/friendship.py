from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class FriendshipModel(Base):
    __tablename__ = "friendships"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_a_id: Mapped[int] = mapped_column(BigInteger)
    user_b_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text)
    responded_at: Mapped[str] = mapped_column(Text, nullable=True)
