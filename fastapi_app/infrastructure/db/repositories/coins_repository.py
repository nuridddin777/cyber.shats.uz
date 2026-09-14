"""
Read-only for now — deliberately not porting spend_coins/add_coins/
refund_coins yet. coins.py is the shared kernel ~15+ other modules depend
on and already has a known fragmentation bug (it writes to treasury_fund
directly instead of going through treasury.py); moving the write path
needs its own focused pass with real unit tests (insufficient balance,
concurrent spend, refunds), not a rushed bundle with the read side.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.domain.coins.entities import CoinTransaction, LeaderboardEntry
from fastapi_app.infrastructure.db.models.user import UserModel
from fastapi_app.infrastructure.db.models.user_rating import UserRatingModel
from fastapi_app.infrastructure.db.models.coin_transaction import CoinTransactionModel


class SqlAlchemyCoinsRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_balance(self, user_id: int) -> int | None:
        user = self._db.get(UserModel, user_id)
        return user.code_balance if user else None

    def get_transactions(self, user_id: int, limit: int) -> list[CoinTransaction]:
        rows = self._db.scalars(
            select(CoinTransactionModel)
            .where(CoinTransactionModel.user_id == user_id)
            .order_by(CoinTransactionModel.id.desc())
            .limit(limit)
        ).all()
        return [
            CoinTransaction(id=r.id, amount=r.amount, reason=r.reason, ref_id=r.ref_id, created_at=r.created_at)
            for r in rows
        ]

    def get_leaderboard(self, limit: int) -> list[LeaderboardEntry]:
        score = func.coalesce(UserRatingModel.total_score, 0)
        rows = self._db.execute(
            select(
                UserModel.id, UserModel.ism, UserModel.familiya, UserModel.level,
                UserModel.code_balance, score.label("total_score"),
                func.coalesce(UserRatingModel.courses_done, 0).label("courses_done"),
            )
            .join(UserRatingModel, UserRatingModel.user_id == UserModel.id, isouter=True)
            .where(UserModel.is_blocked == 0, UserModel.role.notin_(["admin", "mentor"]))
            .order_by(score.desc(), UserModel.xp.desc())
            .limit(limit)
        ).all()
        return [
            LeaderboardEntry(
                id=r.id, ism=r.ism, familiya=r.familiya, level=r.level,
                code_balance=r.code_balance, total_score=r.total_score, courses_done=r.courses_done,
            )
            for r in rows
        ]
