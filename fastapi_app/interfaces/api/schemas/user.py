from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    id: int
    ism: str
    familiya: str
    email: str
    role: str
    plan: str
    xp: int
    level: int
    code_balance: int
    custom_id: str | None
