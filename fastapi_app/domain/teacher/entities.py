from dataclasses import dataclass


@dataclass(frozen=True)
class TeacherGroup:
    id: int
    name: str
    created_at: str


@dataclass(frozen=True)
class TeacherChannel:
    id: int
    name: str
    subscriber_count: int
    created_at: str


@dataclass(frozen=True)
class TeacherDashboard:
    is_teacher: bool
    my_groups: list[TeacherGroup]
    my_channels: list[TeacherChannel]
