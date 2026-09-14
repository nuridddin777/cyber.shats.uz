"""
Eighth FastAPI slice: a user's accepted friends list, READ-ONLY. Mirrors
friends.py's get_friends_list() (online-today friends sorted first).
Sending/accepting/removing friend requests stays in friends.py for now.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.friends.list_friends import list_friends
from fastapi_app.infrastructure.db.repositories.friends_repository import SqlAlchemyFriendsRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.friends import FriendResponse

router = APIRouter(prefix="/api/v2/friends", tags=["friends"])


@router.get("", response_model=list[FriendResponse])
def my_friends(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyFriendsRepository(db)
    return [FriendResponse(**f.__dict__) for f in list_friends(repo, user_id)]
