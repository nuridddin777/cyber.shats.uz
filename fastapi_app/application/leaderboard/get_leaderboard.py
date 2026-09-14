from fastapi_app.domain.leaderboard.entities import LeaderboardEntry
from fastapi_app.domain.leaderboard.repository import LeaderboardRepository


def get_leaderboard(
    repo: LeaderboardRepository, user_id: int, board_type: str, limit: int = 100
) -> tuple[list[LeaderboardEntry], int]:
    if board_type == "code":
        return repo.list_code_board(limit), repo.my_code_rank(user_id)
    return repo.list_xp_board(limit), repo.my_xp_rank(user_id)
