from fastapi_app.domain.users.entities import UserProfile
from fastapi_app.domain.users.repository import UserRepository


def get_profile(repo: UserRepository, user_id: int) -> UserProfile | None:
    return repo.get_profile(user_id)
