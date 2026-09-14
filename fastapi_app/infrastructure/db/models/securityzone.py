from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class SecurityArticleModel(Base):
    __tablename__ = "security_articles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(BigInteger)


class SecurityGlossaryModel(Base):
    __tablename__ = "security_glossary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    term: Mapped[str] = mapped_column(Text)
    definition: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(BigInteger)


class SecurityBlacklistAppModel(Base):
    __tablename__ = "security_blacklist_apps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(BigInteger)


class SecurityChecklistItemModel(Base):
    __tablename__ = "security_checklist_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    category: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(BigInteger)


class UserChecklistProgressModel(Base):
    __tablename__ = "user_checklist_progress"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class UserSecurityScoreModel(Base):
    __tablename__ = "user_security_score"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    score: Mapped[int] = mapped_column(BigInteger)
    total: Mapped[int] = mapped_column(BigInteger)
    level: Mapped[str] = mapped_column(Text)
