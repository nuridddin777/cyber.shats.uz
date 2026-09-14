from fastapi_app.domain.coins.entities import CoinTransaction
from fastapi_app.domain.coins.repository import CoinsRepository


def get_transactions(repo: CoinsRepository, user_id: int, limit: int = 20) -> list[CoinTransaction]:
    return repo.get_transactions(user_id, limit)
