from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.domain.notifications.entities import Notification
from fastapi_app.infrastructure.db.models.notification import NotificationModel


class SqlAlchemyNotificationsRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_for_user(self, user_id: int, limit: int) -> list[Notification]:
        rows = self._db.scalars(
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
        ).all()
        return [
            Notification(
                id=r.id, title=r.title, body=r.body, type=r.type,
                is_read=r.is_read, created_at=r.created_at,
            )
            for r in rows
        ]

    def count_unread(self, user_id: int) -> int:
        return self._db.scalar(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.user_id == user_id, NotificationModel.is_read == 0)
        ) or 0
