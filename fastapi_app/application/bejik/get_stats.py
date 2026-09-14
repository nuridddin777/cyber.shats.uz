from fastapi_app.domain.bejik.entities import BadgeStats
from fastapi_app.domain.bejik.repository import BejikRepository


def get_stats(repo: BejikRepository, user_id: int) -> BadgeStats:
    return repo.get_stats(user_id)
