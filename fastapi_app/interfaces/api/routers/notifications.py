"""
Seventh FastAPI slice: a user's own notifications, READ-ONLY (list +
unread count). Mirrors queries already used throughout app.py. Marking
as read stays on the existing Flask routes for now.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.notifications.list_for_user import list_for_user
from fastapi_app.application.notifications.count_unread import count_unread
from fastapi_app.infrastructure.db.repositories.notifications_repository import SqlAlchemyNotificationsRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.notifications import NotificationResponse, UnreadCountResponse

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def my_notifications(
    limit: int = 40,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db_session),
):
    repo = SqlAlchemyNotificationsRepository(db)
    return [NotificationResponse(**n.__dict__) for n in list_for_user(repo, user_id, limit)]


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyNotificationsRepository(db)
    return UnreadCountResponse(count=count_unread(repo, user_id))
