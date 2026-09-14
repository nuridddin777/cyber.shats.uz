from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.shatslive.entities import LiveStream
from fastapi_app.infrastructure.db.models.livestream import LiveStreamModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyShatsLiveRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_streams(self, limit: int = 30) -> list[LiveStream]:
        rows = self._db.execute(
            select(LiveStreamModel, UserModel)
            .join(UserModel, UserModel.id == LiveStreamModel.host_id)
            .order_by((LiveStreamModel.status == "live").desc(), LiveStreamModel.scheduled_at.desc())
            .limit(limit)
        ).all()
        return [
            LiveStream(id=s.id, title=s.title, description=s.description, scheduled_at=s.scheduled_at,
                       status=s.status, stream_url=s.stream_url, created_at=s.created_at,
                       host_ism=u.ism, host_familiya=u.familiya)
            for s, u in rows
        ]

    def get_user_plan(self, user_id: int) -> str | None:
        return self._db.execute(select(UserModel.plan).where(UserModel.id == user_id)).scalar()
