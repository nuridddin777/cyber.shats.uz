from dataclasses import dataclass


@dataclass(frozen=True)
class Certificate:
    id: int
    course_id: int
    course_title: str
    cert_code: str
    issued_at: str
