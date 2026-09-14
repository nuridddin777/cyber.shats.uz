from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class PremiumIdModel(Base):
    __tablename__ = "premium_ids"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    custom_id: Mapped[str] = mapped_column(Text)
    id_type: Mapped[str] = mapped_column(Text)
    base_price: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text)
    owner_user_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[str] = mapped_column(Text)
