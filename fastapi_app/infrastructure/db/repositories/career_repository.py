from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from fastapi_app.domain.career.entities import JobListing
from fastapi_app.infrastructure.db.models.career import JobApplicationModel, JobListingModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyCareerRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_open(self, viewer_user_id: int) -> list[JobListing]:
        already_applied_sq = exists(
            select(JobApplicationModel.id).where(
                JobApplicationModel.job_id == JobListingModel.id,
                JobApplicationModel.user_id == viewer_user_id,
            )
        )
        rows = self._db.execute(
            select(JobListingModel, already_applied_sq)
            .where(JobListingModel.status == "open")
            .order_by(JobListingModel.created_at.desc())
        ).all()
        return [
            JobListing(id=j.id, title=j.title, company=j.company, description=j.description,
                       location=j.location, status=j.status, created_at=j.created_at,
                       already_applied=bool(applied))
            for j, applied in rows
        ]

    def get_user_plan(self, user_id: int) -> str | None:
        return self._db.execute(select(UserModel.plan).where(UserModel.id == user_id)).scalar()
