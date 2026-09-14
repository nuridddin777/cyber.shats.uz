from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.ids.entities import PremiumId
from fastapi_app.infrastructure.db.models.premium_id import PremiumIdModel


class SqlAlchemyIdsRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_marketplace(self) -> list[PremiumId]:
        rows = self._db.scalars(
            select(PremiumIdModel).order_by(PremiumIdModel.created_at.desc())
        ).all()
        return [
            PremiumId(
                id=r.id, custom_id=r.custom_id, id_type=r.id_type,
                base_price=r.base_price, status=r.status, owner_user_id=r.owner_user_id,
            )
            for r in rows
        ]
