from fastapi_app.domain.coins.entities import LeaderboardEntry
from fastapi_app.domain.coins.repository import CoinsRepository


def get_leaderboard(repo: CoinsRepository, limit: int = 20) -> list[LeaderboardEntry]:
    return repo.get_leaderboard(limit)
