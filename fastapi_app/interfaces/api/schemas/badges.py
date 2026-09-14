from pydantic import BaseModel


class BadgeResponse(BaseModel):
    id: int
    name: str
    icon: str
    description: str
    earned: bool
    earned_at: str | None
