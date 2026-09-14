from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_key: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    stats_members: Mapped[int] = mapped_column(BigInteger)
    stats_projects: Mapped[int] = mapped_column(BigInteger)
    stats_years: Mapped[int] = mapped_column(BigInteger)


class OrganizationPostModel(Base):
    __tablename__ = "organization_posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_key: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text)


class OrganizationRequestModel(Base):
    __tablename__ = "organization_requests"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    org_key: Mapped[str] = mapped_column(Text)
    user_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(Text)
