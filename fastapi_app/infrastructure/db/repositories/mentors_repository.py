from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.mentors.entities import Mentor
from fastapi_app.infrastructure.db.models.mentor import MentorModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyMentorsRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_all(self) -> list[Mentor]:
        rows = self._db.execute(
            select(MentorModel, UserModel)
            .join(UserModel, UserModel.id == MentorModel.user_id)
            .order_by(MentorModel.created_at.desc())
        ).all()
        return [
            Mentor(user_id=m.user_id, skills=m.skills, bio=m.bio, contact=m.contact,
                   created_at=m.created_at, ism=u.ism, familiya=u.familiya, custom_id=u.custom_id)
            for m, u in rows
        ]

    def get_user_plan(self, user_id: int) -> str | None:
        return self._db.execute(select(UserModel.plan).where(UserModel.id == user_id)).scalar()
