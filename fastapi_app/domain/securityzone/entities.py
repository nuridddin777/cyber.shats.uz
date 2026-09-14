from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityArticle:
    id: int
    category: str
    title: str
    slug: str
    summary: str
    order_index: int


@dataclass(frozen=True)
class GlossaryTerm:
    id: int
    term: str
    definition: str


@dataclass(frozen=True)
class BlacklistApp:
    id: int
    name: str
    reason: str


@dataclass(frozen=True)
class ChecklistItem:
    id: int
    category: str
    text: str
    checked: bool


@dataclass(frozen=True)
class SecurityZoneOverview:
    articles: list[SecurityArticle]
    glossary: list[GlossaryTerm]
    blacklist: list[BlacklistApp]
    checklist: list[ChecklistItem]
    checklist_done: int
    checklist_total: int
    user_score: int | None
    user_level: str | None
