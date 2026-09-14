from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from fastapi_app.domain.groups.entities import Group
from fastapi_app.infrastructure.db.models.group import GroupMemberModel, GroupModel
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemyGroupsRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_all(self, viewer_user_id: int, limit: int = 50) -> list[Group]:
        my_membership = aliased(GroupMemberModel)
        rows = self._db.execute(
            select(GroupModel, UserModel, my_membership.role)
            .join(UserModel, UserModel.id == GroupModel.owner_id)
            .outerjoin(
                my_membership,
                (my_membership.group_id == GroupModel.id) & (my_membership.user_id == viewer_user_id),
            )
            .order_by(GroupModel.member_count.desc(), GroupModel.id.desc())
            .limit(limit)
        ).all()
        return [
            Group(
                id=g.id, name=g.name, description=g.description, avatar=g.avatar,
                public_id=g.public_id, is_public=g.is_public, member_count=g.member_count,
                created_at=g.created_at, owner_id=owner.id, owner_ism=owner.ism,
                owner_familiya=owner.familiya, is_member=my_role is not None, my_role=my_role,
            )
            for g, owner, my_role in rows
        ]
