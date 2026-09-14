from dataclasses import dataclass


@dataclass(frozen=True)
class Badge:
    id: int
    name: str
    icon: str
    description: str
    earned: bool
    earned_at: str | None
