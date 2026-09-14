from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.organization.entities import Organization, OrganizationPost
from fastapi_app.infrastructure.db.models.organization import (
    OrganizationModel, OrganizationPostModel, OrganizationRequestModel,
)
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyOrganizationRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_by_key(self, org_key: str) -> Organization | None:
        o = self._db.execute(select(OrganizationModel).where(OrganizationModel.org_key == org_key)).scalar()
        if not o:
            return None
        return Organization(id=o.id, org_key=o.org_key, name=o.name, description=o.description,
                             stats_members=o.stats_members, stats_projects=o.stats_projects,
                             stats_years=o.stats_years)

    def list_posts(self, org_key: str, limit: int = 20) -> list[OrganizationPost]:
        rows = self._db.execute(
            select(OrganizationPostModel)
            .where(OrganizationPostModel.org_key == org_key)
            .order_by(OrganizationPostModel.created_at.desc())
            .limit(limit)
        ).scalars().all()
        return [OrganizationPost(id=p.id, title=p.title, content=p.content, created_at=p.created_at) for p in rows]

    def get_my_latest_request_status(self, org_key: str, user_id: int) -> str | None:
        return self._db.execute(
            select(OrganizationRequestModel.status)
            .where(OrganizationRequestModel.org_key == org_key, OrganizationRequestModel.user_id == user_id)
            .order_by(OrganizationRequestModel.id.desc())
            .limit(1)
        ).scalar()

    def get_user_plan(self, user_id: int) -> str | None:
        return self._db.execute(select(UserModel.plan).where(UserModel.id == user_id)).scalar()
