from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class PrivateMessageModel(Base):
    __tablename__ = "private_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sender_id: Mapped[int] = mapped_column(BigInteger)
    receiver_id: Mapped[int] = mapped_column(BigInteger)
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[str] = mapped_column(Text)
