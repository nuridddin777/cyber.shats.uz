from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi_app.domain.bejik.entities import BadgeStats, QrScan
from fastapi_app.infrastructure.db.models.qrscan import QrScanLogModel


class SqlAlchemyBejikRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_stats(self, user_id: int) -> BadgeStats:
        scan_count = self._db.execute(
            select(func.count()).select_from(QrScanLogModel).where(QrScanLogModel.badge_user_id == user_id)
        ).scalar()
        rows = self._db.execute(
            select(QrScanLogModel)
            .where(QrScanLogModel.badge_user_id == user_id)
            .order_by(QrScanLogModel.scanned_at.desc())
            .limit(15)
        ).scalars().all()
        recent = [QrScan(id=r.id, scanned_at=r.scanned_at, scanner_ip=r.scanner_ip) for r in rows]
        return BadgeStats(scan_count=scan_count, recent_scans=recent)
