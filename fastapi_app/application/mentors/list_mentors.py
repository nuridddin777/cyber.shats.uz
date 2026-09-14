from fastapi_app.domain.mentors.entities import Mentor
from fastapi_app.domain.mentors.repository import MentorsRepository


class NotHackerPlanError(Exception):
    pass


def list_mentors(repo: MentorsRepository, user_id: int) -> list[Mentor]:
    if repo.get_user_plan(user_id) != "hacker":
        raise NotHackerPlanError()
    return repo.list_all()
