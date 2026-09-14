from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.domain.leaderboard.entities import LeaderboardEntry
from fastapi_app.infrastructure.db.models.user import UserModel
from fastapi_app.infrastructure.db.models.user_rating import UserRatingModel


class SqlAlchemyLeaderboardRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_xp_board(self, limit: int = 100) -> list[LeaderboardEntry]:
        rows = self._db.execute(
            select(UserModel, UserRatingModel)
            .outerjoin(UserRatingModel, UserRatingModel.user_id == UserModel.id)
            .where(UserModel.is_blocked == 0, UserModel.role.notin_(["admin", "mentor"]))
            .order_by(func.coalesce(UserRatingModel.total_score, 0).desc(), UserModel.xp.desc())
            .limit(limit)
        ).all()
        return [
            LeaderboardEntry(
                id=u.id, ism=u.ism, familiya=u.familiya, avatar=u.avatar, level=u.level,
                plan=u.plan, code_balance=u.code_balance,
                total_score=(r.total_score if r else 0), courses_done=(r.courses_done if r else 0),
                rank_position=(r.rank_position if r else 0),
            )
            for u, r in rows
        ]

    def list_code_board(self, limit: int = 100) -> list[LeaderboardEntry]:
        rows = self._db.execute(
            select(UserModel)
            .where(UserModel.role == "student", UserModel.code_balance > 0)
            .order_by(UserModel.code_balance.desc())
            .limit(limit)
        ).scalars().all()
        return [
            LeaderboardEntry(
                id=u.id, ism=u.ism, familiya=u.familiya, avatar=u.avatar, level=u.level,
                plan=u.plan, code_balance=u.code_balance, total_score=u.code_balance,
                courses_done=0, rank_position=0,
            )
            for u in rows
        ]

    def my_xp_rank(self, user_id: int) -> int:
        row = self._db.execute(
            select(UserRatingModel.rank_position).where(UserRatingModel.user_id == user_id)
        ).first()
        return row.rank_position if row else 0

    def my_code_rank(self, user_id: int) -> int:
        user = self._db.get(UserModel, user_id)
        if not user or not user.code_balance or user.code_balance <= 0:
            return 0
        count = self._db.execute(
            select(func.count()).select_from(UserModel)
            .where(UserModel.role == "student", UserModel.code_balance > user.code_balance)
        ).scalar()
        return count + 1
