from dataclasses import dataclass


@dataclass(frozen=True)
class Organization:
    id: int
    org_key: str
    name: str
    description: str
    stats_members: int
    stats_projects: int
    stats_years: int


@dataclass(frozen=True)
class OrganizationPost:
    id: int
    title: str
    content: str
    created_at: str


@dataclass(frozen=True)
class OrganizationPageData:
    org: Organization | None
    posts: list[OrganizationPost]
    my_request_status: str | None
