from fastapi_app.domain.notifications.entities import Notification
from fastapi_app.domain.notifications.repository import NotificationsRepository


def list_for_user(repo: NotificationsRepository, user_id: int, limit: int = 40) -> list[Notification]:
    return repo.list_for_user(user_id, limit)
