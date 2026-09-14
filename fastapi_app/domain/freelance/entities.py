from dataclasses import dataclass


@dataclass(frozen=True)
class FreelanceGig:
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
