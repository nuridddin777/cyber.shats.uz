from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class LiveStreamModel(Base):
    __tablename__ = "live_streams"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    host_id: Mapped[int] = mapped_column(BigInteger)
    scheduled_at: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)
    stream_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)
