from pydantic import BaseModel


class CourseResponse(BaseModel):
    id: int
    slug: str
    title: str
    subtitle: str | None
    description: str | None
    level: str | None
    duration_weeks: int | None
    lessons_count: int | None
    students_count: int
    rating: float | None
    price: int
    icon: str
    code_price: int | None
    is_pro_only: int
    is_paid: int
    direction_id: int
    direction_name: str
    direction_slug: str


class DirectionResponse(BaseModel):
    id: int
    slug: str
    name_uz: str
    icon: str | None
    description: str | None
    color: str | None


class CoursesListResponse(BaseModel):
    courses: list[CourseResponse]
    directions: list[DirectionResponse]
