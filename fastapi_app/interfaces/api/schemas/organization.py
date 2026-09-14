from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    id: int
    org_key: str
    name: str
    description: str
    stats_members: int
    stats_projects: int
    stats_years: int


class OrganizationPostResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: str


class OrganizationPageResponse(BaseModel):
    org: OrganizationResponse | None
    posts: list[OrganizationPostResponse]
    my_request_status: str | None
