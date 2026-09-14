from fastapi_app.domain.career.entities import JobListing
from fastapi_app.domain.career.repository import CareerRepository


class NotHackerPlanError(Exception):
    pass


def list_open_jobs(repo: CareerRepository, user_id: int) -> list[JobListing]:
    if repo.get_user_plan(user_id) != "hacker":
        raise NotHackerPlanError()
    return repo.list_open(user_id)
