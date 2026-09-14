from fastapi_app.domain.notifications.repository import NotificationsRepository


def count_unread(repo: NotificationsRepository, user_id: int) -> int:
    return repo.count_unread(user_id)
