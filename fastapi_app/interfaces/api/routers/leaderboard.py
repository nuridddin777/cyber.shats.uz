"""
Seventeenth FastAPI slice: leaderboard (XP or CODE board), READ-ONLY.
Mirrors app.py's leaderboard() route: coins.get_leaderboard() for the XP
board, an inline query for the CODE board, plus the viewer's own rank in
whichever board is requested. The badges-progress panel on that same page
stays out of scope (already covered by the badges slice).
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.application.leaderboard.get_leaderboard import get_leaderboard
from fastapi_app.infrastructure.db.repositories.leaderboard_repository import SqlAlchemyLeaderboardRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.leaderboard import LeaderboardEntryResponse, LeaderboardResponse

router = APIRouter(prefix="/api/v2/leaderboard", tags=["leaderboard"])


@router.get("", response_model=LeaderboardResponse)
def leaderboard(
    type: str = Query(default="xp", pattern="^(xp|code)$"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyLeaderboardRepository(db)
    leaders, my_rank = get_leaderboard(repo, user_id, type)
    return LeaderboardResponse(
        leaders=[LeaderboardEntryResponse(**e.__dict__) for e in leaders],
        my_rank=my_rank,
    )
