from typing import Protocol

from fastapi_app.domain.notifications.entities import Notification


class NotificationsRepository(Protocol):
    def list_for_user(self, user_id: int, limit: int) -> list[Notification]: ...
    def count_unread(self, user_id: int) -> int: ...
