from pydantic import BaseModel


class LeaderboardEntryResponse(BaseModel):
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


class LeaderboardResponse(BaseModel):
    leaders: list[LeaderboardEntryResponse]
    my_rank: int
