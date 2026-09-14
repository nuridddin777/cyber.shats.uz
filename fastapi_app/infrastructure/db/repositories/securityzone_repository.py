from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.securityzone.entities import (
    BlacklistApp, ChecklistItem, GlossaryTerm, SecurityArticle, SecurityZoneOverview,
)
from fastapi_app.infrastructure.db.models.securityzone import (
    SecurityArticleModel, SecurityBlacklistAppModel, SecurityChecklistItemModel,
    SecurityGlossaryModel, UserChecklistProgressModel, UserSecurityScoreModel,
)
from fastapi_app.infrastructure.db.models.user import UserModel


class SqlAlchemySecurityZoneRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_overview(self, user_id: int) -> SecurityZoneOverview:
        articles = [
            SecurityArticle(id=a.id, category=a.category, title=a.title, slug=a.slug,
                             summary=a.summary, order_index=a.order_index)
            for a in self._db.execute(
                select(SecurityArticleModel).order_by(
                    SecurityArticleModel.category, SecurityArticleModel.order_index, SecurityArticleModel.id
                )
            ).scalars().all()
        ]
        glossary = [
            GlossaryTerm(id=g.id, term=g.term, definition=g.definition)
            for g in self._db.execute(
                select(SecurityGlossaryModel).order_by(
                    SecurityGlossaryModel.order_index, SecurityGlossaryModel.term
                )
            ).scalars().all()
        ]
        blacklist = [
            BlacklistApp(id=b.id, name=b.name, reason=b.reason)
            for b in self._db.execute(
                select(SecurityBlacklistAppModel).order_by(
                    SecurityBlacklistAppModel.order_index, SecurityBlacklistAppModel.id
                )
            ).scalars().all()
        ]
        checked_ids = set(
            self._db.execute(
                select(UserChecklistProgressModel.item_id).where(UserChecklistProgressModel.user_id == user_id)
            ).scalars().all()
        )
        checklist_items = self._db.execute(
            select(SecurityChecklistItemModel).order_by(
                SecurityChecklistItemModel.category, SecurityChecklistItemModel.order_index,
                SecurityChecklistItemModel.id,
            )
        ).scalars().all()
        checklist = [
            ChecklistItem(id=it.id, category=it.category, text=it.text, checked=it.id in checked_ids)
            for it in checklist_items
        ]
        done = sum(1 for it in checklist if it.checked)

        score_row = self._db.get(UserSecurityScoreModel, user_id)

        return SecurityZoneOverview(
            articles=articles, glossary=glossary, blacklist=blacklist, checklist=checklist,
            checklist_done=done, checklist_total=len(checklist),
            user_score=score_row.score if score_row else None,
            user_level=score_row.level if score_row else None,
        )

    def get_user_plan(self, user_id: int) -> str | None:
        return self._db.execute(select(UserModel.plan).where(UserModel.id == user_id)).scalar()
