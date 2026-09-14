from pydantic import BaseModel


class FreelanceGigResponse(BaseModel):
    id: int
    gig_type: str
    title: str
    description: str
    price_code: int
    status: str
    created_at: str
    ism: str
    familiya: str
    custom_id: str | None
