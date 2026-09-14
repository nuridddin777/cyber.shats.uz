from fastapi_app.domain.messages.repository import MessagesRepository


def count_unread(repo: MessagesRepository, user_id: int) -> int:
    return repo.count_unread(user_id)
