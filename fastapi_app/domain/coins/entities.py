from dataclasses import dataclass


@dataclass(frozen=True)
class CoinTransaction:
    id: int
    amount: int
    reason: str
    ref_id: int | None
    created_at: str


@dataclass(frozen=True)
class LeaderboardEntry:
    id: int
    ism: str
    familiya: str
    level: int
    code_balance: int
    total_score: int
    courses_done: int
