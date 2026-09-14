from dataclasses import dataclass


@dataclass(frozen=True)
class LeaderboardEntry:
    id: int
    ism: str
    familiya: str
    avatar: str | None
    level: int
    plan: str
    code_balance: int
    total_score: int
    courses_done: int
    rank_position: int
