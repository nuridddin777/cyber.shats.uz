from fastapi_app.domain.shatslive.entities import LiveStream
from fastapi_app.domain.shatslive.repository import ShatsLiveRepository


class NotHackerPlanError(Exception):
    pass


def list_streams(repo: ShatsLiveRepository, user_id: int, limit: int = 30) -> list[LiveStream]:
    if repo.get_user_plan(user_id) != "hacker":
        raise NotHackerPlanError()
    return repo.list_streams(limit)
