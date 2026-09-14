from pydantic import BaseModel


class IncubatorIdeaResponse(BaseModel):
    id: int
    title: str
    description: str
    stage: str
    created_at: str
    ism: str
    familiya: str
    vote_count: int
    voted_by_me: bool
