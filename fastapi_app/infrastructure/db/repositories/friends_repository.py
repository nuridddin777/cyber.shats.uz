import datetime

from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session, aliased

from fastapi_app.domain.friends.entities import Friend
from fastapi_app.infrastructure.db.models.user import UserModel
from fastapi_app.infrastructure.db.models.friendship import FriendshipModel


class SqlAlchemyFriendsRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_friends(self, user_id: int) -> list[Friend]:
        f = FriendshipModel
        u = aliased(UserModel)
        peer_id = case((f.user_a_id == user_id, f.user_b_id), else_=f.user_a_id)
        today = datetime.datetime.utcnow().date().isoformat()

        rows = self._db.execute(
            select(u, f.responded_at)
            .join(f, u.id == peer_id)
            .where(or_(f.user_a_id == user_id, f.user_b_id == user_id), f.status == "accepted")
            .order_by((u.last_login_date == today).desc(), f.responded_at.desc())
        ).all()
        return [
            Friend(
                id=user.id, ism=user.ism, familiya=user.familiya, custom_id=user.custom_id,
                avatar_path=user.avatar_path, level=user.level, last_login_date=user.last_login_date,
            )
            for user, _responded_at in rows
        ]
