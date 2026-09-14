from pydantic import BaseModel


class ForumPostResponse(BaseModel):
    id: int
    title: str
    body: str
    category: str
    views: int
    replies_count: int
    created_at: str
    author_id: int
    author_ism: str
    author_familiya: str
    author_avatar: str | None


class ForumCategoryResponse(BaseModel):
    category: str
    post_count: int
