from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class NotificationModel(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    # SQLite-era 0/1 flag, migrated as BIGINT — not native boolean.
    is_read: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[str] = mapped_column(Text)
