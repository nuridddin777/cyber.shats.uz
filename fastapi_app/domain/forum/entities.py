from dataclasses import dataclass


@dataclass(frozen=True)
class ForumPost:
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


@dataclass(frozen=True)
class ForumCategory:
    category: str
    post_count: int
