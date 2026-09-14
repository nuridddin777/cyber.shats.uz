from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: int
    title: str
    body: str
    type: str
    is_read: int
    created_at: str


class UnreadCountResponse(BaseModel):
    count: int
