from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class QrScanLogModel(Base):
    __tablename__ = "qr_scan_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    badge_user_id: Mapped[int] = mapped_column(BigInteger)
    scanned_at: Mapped[str] = mapped_column(Text)
    scanner_ip: Mapped[str] = mapped_column(Text)
