from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.freelance.entities import FreelanceGig
from fastapi_app.infrastructure.db.models.freelance import FreelanceGigModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyFreelanceRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_open(self, limit: int = 50) -> list[FreelanceGig]:
        rows = self._db.execute(
            select(FreelanceGigModel, UserModel)
            .join(UserModel, UserModel.id == FreelanceGigModel.user_id)
            .where(FreelanceGigModel.status == "open")
            .order_by(FreelanceGigModel.created_at.desc())
            .limit(limit)
        ).all()
        return [
            FreelanceGig(id=g.id, gig_type=g.gig_type, title=g.title, description=g.description,
                         price_code=g.price_code, status=g.status, created_at=g.created_at,
                         ism=u.ism, familiya=u.familiya, custom_id=u.custom_id)
            for g, u in rows
        ]

    def get_user_plan(self, user_id: int) -> str | None:
        return self._db.execute(select(UserModel.plan).where(UserModel.id == user_id)).scalar()
