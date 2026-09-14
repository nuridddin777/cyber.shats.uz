from dataclasses import dataclass


@dataclass(frozen=True)
class Notification:
    id: int
    title: str
    body: str
    type: str
    is_read: int
    created_at: str
