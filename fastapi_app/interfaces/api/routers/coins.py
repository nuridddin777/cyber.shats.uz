"""
Third FastAPI slice: coins, READ-ONLY (GET /balance, GET /transactions).

coins.py is the shared kernel ~15+ other modules depend on for real-money
operations (spend/add/refund coins) and has a known bug (writes to
treasury_fund directly, bypassing treasury.py). Deliberately not porting
the write path in this pass — that needs its own focused change with real
unit tests for insufficient balance / concurrent spend / refunds, not a
rushed bundle with this read-only slice. All writes still go through the
existing coins.py exactly as before.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.coins.get_balance import get_balance
from fastapi_app.application.coins.get_transactions import get_transactions
from fastapi_app.application.coins.get_leaderboard import get_leaderboard
from fastapi_app.infrastructure.db.repositories.coins_repository import SqlAlchemyCoinsRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.coins import (
    BalanceResponse, TransactionResponse, LeaderboardEntryResponse,
)

router = APIRouter(prefix="/api/v2/coins", tags=["coins"])


@router.get("/balance", response_model=BalanceResponse)
def balance(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyCoinsRepository(db)
    bal = get_balance(repo, user_id)
    if bal is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return BalanceResponse(balance=bal)


@router.get("/transactions", response_model=list[TransactionResponse])
def transactions(
    limit: int = 20,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyCoinsRepository(db)
    txns = get_transactions(repo, user_id, limit)
    return [TransactionResponse(**t.__dict__) for t in txns]


@router.get("/leaderboard", response_model=list[LeaderboardEntryResponse])
def leaderboard(limit: int = 20, db: Session = Depends(get_db_session)):
    # Public — mirrors coins.py's get_leaderboard(), no auth required.
    repo = SqlAlchemyCoinsRepository(db)
    entries = get_leaderboard(repo, limit)
    return [LeaderboardEntryResponse(**e.__dict__) for e in entries]
