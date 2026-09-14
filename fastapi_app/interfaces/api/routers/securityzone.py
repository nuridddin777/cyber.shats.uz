"""
Twenty-second FastAPI slice: security zone overview, READ-ONLY. Mirrors
secz_routes.py's security_zone_page() route (articles by category,
glossary, blacklist apps, checklist + progress, user's score), including
its MAXSUS/hacker-plan gate. The quiz, password checker, checklist
toggle, and certificate PDF stay on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.securityzone.get_overview import NotHackerPlanError, get_overview
from fastapi_app.infrastructure.db.repositories.securityzone_repository import SqlAlchemySecurityZoneRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.securityzone import (
    BlacklistAppResponse, ChecklistItemResponse, GlossaryTermResponse, SecurityArticleResponse,
    SecurityZoneOverviewResponse,
)

router = APIRouter(prefix="/api/v2/security-zone", tags=["security-zone"])


@router.get("", response_model=SecurityZoneOverviewResponse)
def security_zone(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemySecurityZoneRepository(db)
    try:
        overview = get_overview(repo, user_id)
    except NotHackerPlanError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.")
    return SecurityZoneOverviewResponse(
        articles=[SecurityArticleResponse(**a.__dict__) for a in overview.articles],
        glossary=[GlossaryTermResponse(**g.__dict__) for g in overview.glossary],
        blacklist=[BlacklistAppResponse(**b.__dict__) for b in overview.blacklist],
        checklist=[ChecklistItemResponse(**c.__dict__) for c in overview.checklist],
        checklist_done=overview.checklist_done,
        checklist_total=overview.checklist_total,
        user_score=overview.user_score,
        user_level=overview.user_level,
    )
