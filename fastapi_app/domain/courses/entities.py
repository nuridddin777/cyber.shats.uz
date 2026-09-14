from dataclasses import dataclass


@dataclass(frozen=True)
class Course:
    id: int
    slug: str
    title: str
    subtitle: str
    description: str
    level: str
    duration_weeks: int
    lessons_count: int
    students_count: int
    rating: float
    price: int
    icon: str
    code_price: int
    is_pro_only: int
    is_paid: int
    direction_id: int
    direction_name: str
    direction_slug: str


@dataclass(frozen=True)
class Direction:
    id: int
    slug: str
    name_uz: str
    icon: str
    description: str
    color: str
