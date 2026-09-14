from typing import Protocol

from fastapi_app.domain.friends.entities import Friend


class FriendsRepository(Protocol):
    def list_friends(self, user_id: int) -> list[Friend]: ...
