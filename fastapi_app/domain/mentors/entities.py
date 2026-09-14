from dataclasses import dataclass


@dataclass(frozen=True)
class Mentor:
    user_id: int
    skills: str
    bio: str
    contact: str
    created_at: str
    ism: str
    familiya: str
    custom_id: str | None
