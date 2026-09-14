from pydantic import BaseModel


class BalanceResponse(BaseModel):
    balance: int


class TransactionResponse(BaseModel):
    id: int
    amount: int
    reason: str
    ref_id: int | None
    created_at: str


class LeaderboardEntryResponse(BaseModel):
    id: int
    ism: str
    familiya: str
    level: int
    code_balance: int
    total_score: int
    courses_done: int
