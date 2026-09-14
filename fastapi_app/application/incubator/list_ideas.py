from fastapi_app.domain.incubator.entities import IncubatorIdea
from fastapi_app.domain.incubator.repository import IncubatorRepository


class NotHackerPlanError(Exception):
    pass


def list_ideas(repo: IncubatorRepository, user_id: int) -> list[IncubatorIdea]:
    if repo.get_user_plan(user_id) != "hacker":
        raise NotHackerPlanError()
    return repo.list_ideas(user_id)
