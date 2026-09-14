from fastapi_app.domain.coins.repository import CoinsRepository


def get_balance(repo: CoinsRepository, user_id: int) -> int | None:
    return repo.get_balance(user_id)
