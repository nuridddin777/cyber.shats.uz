from pydantic import BaseModel


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    avatar: str | None
    public_id: str | None
    is_public: int
    member_count: int
    created_at: str
    owner_id: int
    owner_ism: str
    owner_familiya: str
    is_member: bool
    my_role: str | None
