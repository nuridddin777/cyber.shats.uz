"""
Sixteenth FastAPI slice: book library + news feed, READ-ONLY. Mirrors
library_routes.py's library() and news() routes. No per-user access
control on either — same content for every logged-in user.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from fastapi_app.application.library.list_content import list_books, list_news
from fastapi_app.infrastructure.db.repositories.library_repository import SqlAlchemyLibraryRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.library import BookResponse, NewsItemResponse

router = APIRouter(prefix="/api/v2", tags=["library"])


@router.get("/books", response_model=list[BookResponse])
def books(
    cat: str | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyLibraryRepository(db)
    return [BookResponse(**b.__dict__) for b in list_books(repo, cat)]


@router.get("/news", response_model=list[NewsItemResponse])
def news(
    cat: str | None = Query(default=None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyLibraryRepository(db)
    return [NewsItemResponse(**n.__dict__) for n in list_news(repo, cat)]
