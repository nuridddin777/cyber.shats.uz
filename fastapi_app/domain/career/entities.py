from dataclasses import dataclass


@dataclass(frozen=True)
class JobListing:
    id: int
    title: str
    company: str
    description: str
    location: str
    status: str
    created_at: str
    already_applied: bool
