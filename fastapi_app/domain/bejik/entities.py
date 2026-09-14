from dataclasses import dataclass


@dataclass(frozen=True)
class QrScan:
    id: int
    scanned_at: str
    scanner_ip: str


@dataclass(frozen=True)
class BadgeStats:
    scan_count: int
    recent_scans: list[QrScan]
