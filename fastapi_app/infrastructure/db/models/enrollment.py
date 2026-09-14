from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class EnrollmentModel(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    course_id: Mapped[int] = mapped_column(BigInteger)
    progress_percent: Mapped[int] = mapped_column(BigInteger)
    started_at: Mapped[str] = mapped_column(Text)
    completed_at: Mapped[str] = mapped_column(Text, nullable=True)
