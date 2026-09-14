from pydantic import BaseModel


class QrScanResponse(BaseModel):
    id: int
    scanned_at: str
    scanner_ip: str


class BadgeStatsResponse(BaseModel):
    scan_count: int
    recent_scans: list[QrScanResponse]
