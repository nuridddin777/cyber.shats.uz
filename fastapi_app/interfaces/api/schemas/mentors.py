from pydantic import BaseModel


class MentorResponse(BaseModel):
    user_id: int
    skills: str
    bio: str
    contact: str
    created_at: str
    ism: str
    familiya: str
    custom_id: str | None
