from pydantic import BaseModel


class SecurityArticleResponse(BaseModel):
    id: int
    category: str
    title: str
    slug: str
    summary: str
    order_index: int


class GlossaryTermResponse(BaseModel):
    id: int
    term: str
    definition: str


class BlacklistAppResponse(BaseModel):
    id: int
    name: str
    reason: str


class ChecklistItemResponse(BaseModel):
    id: int
    category: str
    text: str
    checked: bool


class SecurityZoneOverviewResponse(BaseModel):
    articles: list[SecurityArticleResponse]
    glossary: list[GlossaryTermResponse]
    blacklist: list[BlacklistAppResponse]
    checklist: list[ChecklistItemResponse]
    checklist_done: int
    checklist_total: int
    user_score: int | None
    user_level: str | None
