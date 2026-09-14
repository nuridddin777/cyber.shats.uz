from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class CoinTransactionModel(Base):
    __tablename__ = "code_transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    amount: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str] = mapped_column(Text)
    ref_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[str] = mapped_column(Text)
