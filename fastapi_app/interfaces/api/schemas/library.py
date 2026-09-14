from pydantic import BaseModel


class BookResponse(BaseModel):
    id: int
    title: str
    type: str
    size_label: str
    category: str
    file_url: str


class NewsItemResponse(BaseModel):
    id: int
    title: str
    summary: str
    source: str
    category: str
    published_at: str
    url: str
