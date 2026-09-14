from fastapi_app.domain.organization.entities import OrganizationPageData
from fastapi_app.domain.organization.repository import OrganizationRepository

VALID_ORG_KEYS = ("mat", "jxt", "shats")


class NotHackerPlanError(Exception):
    pass


class InvalidOrgKeyError(Exception):
    pass


def get_organization_page(repo: OrganizationRepository, user_id: int, org_key: str) -> OrganizationPageData:
    if repo.get_user_plan(user_id) != "hacker":
        raise NotHackerPlanError()
    if org_key not in VALID_ORG_KEYS:
        raise InvalidOrgKeyError()
    org = repo.get_by_key(org_key)
    posts = repo.list_posts(org_key)
    my_request_status = repo.get_my_latest_request_status(org_key, user_id)
    return OrganizationPageData(org=org, posts=posts, my_request_status=my_request_status)
