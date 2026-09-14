"""
Twenty-seventh FastAPI slice: badge QR scan stats, READ-ONLY. Mirrors
bejik_routes.py's bejik_page() route (scan count + 15 most recent
scans of the viewer's own badge). The QR image, public verify page,
and PDF stay on the legacy Flask side.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.bejik.get_stats import get_stats
from fastapi_app.infrastructure.db.repositories.bejik_repository import SqlAlchemyBejikRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.bejik import BadgeStatsResponse, QrScanResponse

router = APIRouter(prefix="/api/v2/bejik", tags=["bejik"])


@router.get("", response_model=BadgeStatsResponse)
def bejik(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyBejikRepository(db)
    stats = get_stats(repo, user_id)
    return BadgeStatsResponse(
        scan_count=stats.scan_count,
        recent_scans=[QrScanResponse(**s.__dict__) for s in stats.recent_scans],
    )
