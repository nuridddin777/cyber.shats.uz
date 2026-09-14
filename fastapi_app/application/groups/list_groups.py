from fastapi_app.domain.groups.entities import Group
from fastapi_app.domain.groups.repository import GroupsRepository


def list_groups(repo: GroupsRepository, viewer_user_id: int, limit: int = 50) -> list[Group]:
    return repo.list_all(viewer_user_id, limit)
