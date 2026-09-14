from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.infrastructure.db.models.private_message import PrivateMessageModel


class SqlAlchemyMessagesRepository:
    def __init__(self, db: Session):
        self._db = db

    def count_unread(self, user_id: int) -> int:
        return self._db.scalar(
            select(func.count())
            .select_from(PrivateMessageModel)
            .where(PrivateMessageModel.receiver_id == user_id, PrivateMessageModel.is_read == 0)
        ) or 0
