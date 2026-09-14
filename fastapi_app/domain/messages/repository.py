from typing import Protocol


class MessagesRepository(Protocol):
    def count_unread(self, user_id: int) -> int: ...
