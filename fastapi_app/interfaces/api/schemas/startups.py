from pydantic import BaseModel


class StartupResponse(BaseModel):
    id: int
    name: str
    description: str
    image_path: str | None
    link_url: str | None
    category: str
    view_count: int
    created_at: str
    in_auction: int
    needs_help: int
    author_id: int
    author_ism: str
    author_familiya: str
    author_avatar: str | None
    like_count: int
    liked_by_me: bool
