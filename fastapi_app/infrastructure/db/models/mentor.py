from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class MentorModel(Base):
    __tablename__ = "mentors"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    skills: Mapped[str] = mapped_column(Text)
    bio: Mapped[str] = mapped_column(Text)
    contact: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)
