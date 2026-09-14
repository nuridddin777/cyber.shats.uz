from fastapi_app.domain.securityzone.entities import SecurityZoneOverview
from fastapi_app.domain.securityzone.repository import SecurityZoneRepository


class NotHackerPlanError(Exception):
    pass


def get_overview(repo: SecurityZoneRepository, user_id: int) -> SecurityZoneOverview:
    if repo.get_user_plan(user_id) != "hacker":
        raise NotHackerPlanError()
    return repo.get_overview(user_id)
