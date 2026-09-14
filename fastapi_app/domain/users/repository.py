from typing import Protocol

from fastapi_app.domain.users.entities import UserProfile


class UserRepository(Protocol):
    def get_profile(self, user_id: int) -> UserProfile | None: ...
