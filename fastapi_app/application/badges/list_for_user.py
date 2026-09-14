from fastapi_app.domain.badges.entities import Badge
from fastapi_app.domain.badges.repository import BadgesRepository


def list_for_user(repo: BadgesRepository, user_id: int) -> list[Badge]:
    return repo.list_for_user(user_id)
