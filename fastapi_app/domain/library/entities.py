from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    id: int
    title: str
    type: str
    size_label: str
    category: str
    file_url: str


@dataclass(frozen=True)
class NewsItem:
    id: int
    title: str
    summary: str
    source: str
    category: str
    published_at: str
    url: str
