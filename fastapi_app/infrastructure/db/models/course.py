from sqlalchemy import BigInteger, Double, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class CourseModel(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(Text)
    direction_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    subtitle: Mapped[str] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    level: Mapped[str] = mapped_column(Text, nullable=True)
    duration_weeks: Mapped[int] = mapped_column(BigInteger, nullable=True)
    lessons_count: Mapped[int] = mapped_column(BigInteger, nullable=True)
    students_count: Mapped[int] = mapped_column(BigInteger)
    rating: Mapped[float] = mapped_column(Double, nullable=True)
    price: Mapped[int] = mapped_column(BigInteger)
    icon: Mapped[str] = mapped_column(Text)
    code_price: Mapped[int] = mapped_column(BigInteger, nullable=True)
    is_pro_only: Mapped[int] = mapped_column(BigInteger)
    is_paid: Mapped[int] = mapped_column(BigInteger)
    is_active: Mapped[int] = mapped_column(BigInteger)


class DirectionModel(Base):
    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(Text)
    name_uz: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    color: Mapped[str] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(BigInteger)
    is_active: Mapped[int] = mapped_column(BigInteger)
