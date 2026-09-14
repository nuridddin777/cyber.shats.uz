from pydantic import BaseModel


class TeacherGroupResponse(BaseModel):
    id: int
    name: str
    created_at: str


class TeacherChannelResponse(BaseModel):
    id: int
    name: str
    subscriber_count: int
    created_at: str


class TeacherDashboardResponse(BaseModel):
    is_teacher: bool
    my_groups: list[TeacherGroupResponse]
    my_channels: list[TeacherChannelResponse]
