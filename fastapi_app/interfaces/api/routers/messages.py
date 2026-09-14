"""
Ninth FastAPI slice: unread private-message count, READ-ONLY. Mirrors
messaging.py's get_unread_total(). Conversations/threads/sending stays
in messaging.py — get_conversations() uses CTEs + window functions that
deserve a careful dedicated port, not a rushed one alongside this.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.messages.count_unread import count_unread
from fastapi_app.infrastructure.db.repositories.messages_repository import SqlAlchemyMessagesRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.notifications import UnreadCountResponse

router = APIRouter(prefix="/api/v2/messages", tags=["messages"])


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyMessagesRepository(db)
    return UnreadCountResponse(count=count_unread(repo, user_id))
