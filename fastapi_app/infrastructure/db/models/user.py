"""
Maps the existing `users` table (owned by the legacy Flask app / db.py,
schema unchanged) — read-only usage here, so only the columns this domain
actually needs are declared. Not the full 65+ column table.
"""
from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ism: Mapped[str] = mapped_column(Text)
    familiya: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    plan: Mapped[str] = mapped_column(Text)
    xp: Mapped[int] = mapped_column(BigInteger)
    level: Mapped[int] = mapped_column(BigInteger)
    code_balance: Mapped[int] = mapped_column(BigInteger)
    custom_id: Mapped[str] = mapped_column(Text, nullable=True)
    # SQLite-era 0/1 flag, migrated as BIGINT (not native boolean) — compare
    # against 0/1, don't treat as a Python bool.
    is_blocked: Mapped[int] = mapped_column(BigInteger)
    avatar_path: Mapped[str] = mapped_column(Text, nullable=True)
    avatar: Mapped[str] = mapped_column(Text, nullable=True)
    last_login_date: Mapped[str] = mapped_column(Text, nullable=True)
    primary_direction_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    is_teacher: Mapped[int] = mapped_column(BigInteger, nullable=True)
