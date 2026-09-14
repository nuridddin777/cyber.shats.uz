from pydantic import BaseModel


class JobListingResponse(BaseModel):
    id: int
    title: str
    company: str
    description: str
    location: str
    status: str
    created_at: str
    already_applied: bool
