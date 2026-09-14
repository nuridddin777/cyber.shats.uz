from fastapi_app.domain.freelance.entities import FreelanceGig
from fastapi_app.domain.freelance.repository import FreelanceRepository


class NotHackerPlanError(Exception):
    pass


def list_open_gigs(repo: FreelanceRepository, user_id: int, limit: int = 50) -> list[FreelanceGig]:
    if repo.get_user_plan(user_id) != "hacker":
        raise NotHackerPlanError()
    return repo.list_open(limit)
