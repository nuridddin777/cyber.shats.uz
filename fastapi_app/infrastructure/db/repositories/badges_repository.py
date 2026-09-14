from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.badges.entities import Badge
from fastapi_app.infrastructure.db.models.badge import BadgeModel, UserBadgeModel


class SqlAlchemyBadgesRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_for_user(self, user_id: int) -> list[Badge]:
        rows = self._db.execute(
            select(BadgeModel, UserBadgeModel.earned_at)
            .outerjoin(
                UserBadgeModel,
                (UserBadgeModel.badge_id == BadgeModel.id) & (UserBadgeModel.user_id == user_id),
            )
            .order_by(BadgeModel.id)
        ).all()
        return [
            Badge(
                id=badge.id, name=badge.name, icon=badge.icon, description=badge.description,
                earned=earned_at is not None, earned_at=earned_at,
            )
            for badge, earned_at in rows
        ]
