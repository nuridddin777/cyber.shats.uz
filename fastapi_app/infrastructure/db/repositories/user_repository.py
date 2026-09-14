from sqlalchemy.orm import Session

from fastapi_app.domain.users.entities import UserProfile
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyUserRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_profile(self, user_id: int) -> UserProfile | None:
        row = self._db.get(UserModel, user_id)
        if row is None:
            return None
        return UserProfile(
            id=row.id, ism=row.ism, familiya=row.familiya, email=row.email,
            role=row.role, plan=row.plan, xp=row.xp, level=row.level,
            code_balance=row.code_balance, custom_id=row.custom_id,
        )
