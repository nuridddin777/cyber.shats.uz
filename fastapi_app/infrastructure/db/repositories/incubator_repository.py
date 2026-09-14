from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from fastapi_app.domain.incubator.entities import IncubatorIdea
from fastapi_app.infrastructure.db.models.incubator import IncubatorIdeaModel, IncubatorVoteModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyIncubatorRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_ideas(self, viewer_user_id: int) -> list[IncubatorIdea]:
        vote_count_sq = (
            select(func.count())
            .where(IncubatorVoteModel.idea_id == IncubatorIdeaModel.id)
            .scalar_subquery()
        )
        voted_by_me_sq = exists(
            select(IncubatorVoteModel.idea_id).where(
                IncubatorVoteModel.idea_id == IncubatorIdeaModel.id,
                IncubatorVoteModel.user_id == viewer_user_id,
            )
        )
        rows = self._db.execute(
            select(IncubatorIdeaModel, UserModel, vote_count_sq, voted_by_me_sq)
            .join(UserModel, UserModel.id == IncubatorIdeaModel.user_id)
            .order_by(vote_count_sq.desc(), IncubatorIdeaModel.created_at.desc())
        ).all()
        return [
            IncubatorIdea(
                id=i.id, title=i.title, description=i.description, stage=i.stage,
                created_at=i.created_at, ism=u.ism, familiya=u.familiya,
                vote_count=vote_count, voted_by_me=bool(voted_by_me),
            )
            for i, u, vote_count, voted_by_me in rows
        ]

    def get_user_plan(self, user_id: int) -> str | None:
        return self._db.execute(select(UserModel.plan).where(UserModel.id == user_id)).scalar()
