from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.teacher.entities import TeacherChannel, TeacherGroup
from fastapi_app.infrastructure.db.models.channel import ChannelModel
from fastapi_app.infrastructure.db.models.group import GroupModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyTeacherRepository:
    def __init__(self, db: Session):
        self._db = db

    def is_teacher(self, user_id: int) -> bool:
        user = self._db.get(UserModel, user_id)
        if not user:
            return False
        return bool(user.is_teacher) or user.role in ("admin", "super_admin")

    def list_my_groups(self, user_id: int) -> list[TeacherGroup]:
        rows = self._db.execute(
            select(GroupModel).where(GroupModel.owner_id == user_id).order_by(GroupModel.created_at.desc())
        ).scalars().all()
        return [TeacherGroup(id=g.id, name=g.name, created_at=g.created_at) for g in rows]

    def list_my_channels(self, user_id: int) -> list[TeacherChannel]:
        rows = self._db.execute(
            select(ChannelModel).where(ChannelModel.owner_id == user_id).order_by(ChannelModel.created_at.desc())
        ).scalars().all()
        return [
            TeacherChannel(id=c.id, name=c.name, subscriber_count=c.subscriber_count, created_at=c.created_at)
            for c in rows
        ]
