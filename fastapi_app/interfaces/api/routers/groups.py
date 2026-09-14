"""
Fifteenth FastAPI slice: group listing, READ-ONLY. Mirrors
groups_routes.py's groups_list() route (social.get_all_groups() plus the
viewer's own membership/role, replacing the separate get_user_groups() +
my_group_ids set-comparison the Flask route does in Python). Creating,
joining, leaving, and sending messages stay on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.application.groups.list_groups import list_groups
from fastapi_app.infrastructure.db.repositories.groups_repository import SqlAlchemyGroupsRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.groups import GroupResponse

router = APIRouter(prefix="/api/v2/groups", tags=["groups"])


@router.get("", response_model=list[GroupResponse])
def groups(
    limit: int = Query(default=50, le=200),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyGroupsRepository(db)
    return [GroupResponse(**g.__dict__) for g in list_groups(repo, user_id, limit)]
