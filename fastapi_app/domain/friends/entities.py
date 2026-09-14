from dataclasses import dataclass


@dataclass(frozen=True)
class Friend:
    id: int
    ism: str
    familiya: str
    custom_id: str | None
    avatar_path: str | None
    level: int
    last_login_date: str | None
