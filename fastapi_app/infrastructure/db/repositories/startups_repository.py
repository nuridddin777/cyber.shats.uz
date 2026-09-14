from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from fastapi_app.domain.startups.entities import Startup
from fastapi_app.infrastructure.db.models.startup import StartupLikeModel, StartupModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyStartupsRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_approved(self, viewer_user_id: int, limit: int = 100) -> list[Startup]:
        like_count_sq = (
            select(func.count())
            .where(StartupLikeModel.startup_id == StartupModel.id)
            .scalar_subquery()
        )
        liked_by_me_sq = exists(
            select(StartupLikeModel.id).where(
                StartupLikeModel.startup_id == StartupModel.id,
                StartupLikeModel.user_id == viewer_user_id,
            )
        )
        rows = self._db.execute(
            select(StartupModel, UserModel, like_count_sq, liked_by_me_sq)
            .join(UserModel, UserModel.id == StartupModel.user_id)
            .where(StartupModel.status == "approved")
            .order_by(StartupModel.id.desc())
            .limit(limit)
        ).all()
        return [
            Startup(
                id=s.id, name=s.name, description=s.description, image_path=s.image_path,
                link_url=s.link_url, category=s.category, view_count=s.view_count,
                created_at=s.created_at, in_auction=s.in_auction, needs_help=s.needs_help,
                author_id=user.id, author_ism=user.ism, author_familiya=user.familiya,
                author_avatar=user.avatar, like_count=like_count, liked_by_me=bool(liked_by_me),
            )
            for s, user, like_count, liked_by_me in rows
        ]
