from fastapi_app.domain.friends.entities import Friend
from fastapi_app.domain.friends.repository import FriendsRepository


def list_friends(repo: FriendsRepository, user_id: int) -> list[Friend]:
    return repo.list_friends(user_id)
