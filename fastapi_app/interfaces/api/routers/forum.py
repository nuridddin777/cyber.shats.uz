"""
Twelfth FastAPI slice: forum post listing + category counts, READ-ONLY.
Mirrors the query used in app.py's forum() route (forum_routes.py).
Posting, replying, and the view-count increment on post detail stay on
the legacy Flask side for now.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.application.forum.list_posts import list_categories, list_posts
from fastapi_app.infrastructure.db.repositories.forum_repository import SqlAlchemyForumRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.forum import ForumCategoryResponse, ForumPostResponse

router = APIRouter(prefix="/api/v2/forum", tags=["forum"])


@router.get("/posts", response_model=list[ForumPostResponse])
def forum_posts(
    category: str | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyForumRepository(db)
    return [ForumPostResponse(**p.__dict__) for p in list_posts(repo, category)]


@router.get("/categories", response_model=list[ForumCategoryResponse])
def forum_categories(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyForumRepository(db)
    return [ForumCategoryResponse(**c.__dict__) for c in list_categories(repo)]
