from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.domain.forum.entities import ForumCategory, ForumPost
from fastapi_app.infrastructure.db.models.forum_post import ForumPostModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyForumRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_posts(self, category: str | None, limit: int) -> list[ForumPost]:
        query = (
            select(ForumPostModel, UserModel)
            .join(UserModel, UserModel.id == ForumPostModel.user_id)
        )
        if category:
            query = query.where(ForumPostModel.category == category)
        query = query.order_by(ForumPostModel.created_at.desc()).limit(limit)
        rows = self._db.execute(query).all()
        return [
            ForumPost(
                id=post.id, title=post.title, body=post.body, category=post.category,
                views=post.views, replies_count=post.replies_count, created_at=post.created_at,
                author_id=user.id, author_ism=user.ism, author_familiya=user.familiya,
                author_avatar=user.avatar,
            )
            for post, user in rows
        ]

    def list_categories(self) -> list[ForumCategory]:
        rows = self._db.execute(
            select(ForumPostModel.category, func.count().label("c")).group_by(ForumPostModel.category)
        ).all()
        return [ForumCategory(category=row.category, post_count=row.c) for row in rows]
