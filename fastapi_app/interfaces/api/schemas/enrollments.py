from pydantic import BaseModel


class EnrollmentResponse(BaseModel):
    id: int
    course_id: int
    title: str
    slug: str
    icon: str
    progress_percent: int
    started_at: str
    completed_at: str | None
