"""
Twenty-fourth FastAPI slice: MAXSUS organization page (mat/jxt/shats),
READ-ONLY. Mirrors tashkilot_routes.py's organization_page() route,
including its org_key whitelist and MAXSUS/hacker-plan gate. Submitting
a join request stays on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.organization.get_page import (
    InvalidOrgKeyError, NotHackerPlanError, get_organization_page,
)
from fastapi_app.infrastructure.db.repositories.organization_repository import SqlAlchemyOrganizationRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.organization import (
    OrganizationPageResponse, OrganizationPostResponse, OrganizationResponse,
)

router = APIRouter(prefix="/api/v2/organizations", tags=["organizations"])


@router.get("/{org_key}", response_model=OrganizationPageResponse)
def organization(org_key: str, user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyOrganizationRepository(db)
    try:
        data = get_organization_page(repo, user_id, org_key)
    except NotHackerPlanError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.")
    except InvalidOrgKeyError:
        raise HTTPException(status_code=404, detail="Tashkilot topilmadi.")
    return OrganizationPageResponse(
        org=OrganizationResponse(**data.org.__dict__) if data.org else None,
        posts=[OrganizationPostResponse(**p.__dict__) for p in data.posts],
        my_request_status=data.my_request_status,
    )
