from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class GroupModel(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    avatar: Mapped[str] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(BigInteger)
    is_public: Mapped[int] = mapped_column(BigInteger)
    member_count: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[str] = mapped_column(Text)
    public_id: Mapped[str] = mapped_column(Text, nullable=True)


class GroupMemberModel(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    role: Mapped[str] = mapped_column(Text)
    joined_at: Mapped[str] = mapped_column(Text)
