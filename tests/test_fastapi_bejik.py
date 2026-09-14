from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.bejik.entities import BadgeStats, QrScan

client = TestClient(app)


class _FakeRepo:
    def __init__(self, stats):
        self._stats = stats

    def get_stats(self, user_id):
        return self._stats


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.bejik as bejik_module
    bejik_module.SqlAlchemyBejikRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/bejik")
    assert resp.status_code == 401


def test_returns_scan_stats():
    scan = QrScan(id=1, scanned_at="2026-01-01 10:00:00", scanner_ip="1.2.3.4")
    _override(_FakeRepo(BadgeStats(scan_count=5, recent_scans=[scan])))
    resp = client.get("/api/v2/bejik")
    assert resp.status_code == 200
    body = resp.json()
    assert body["scan_count"] == 5
    assert body["recent_scans"][0]["scanner_ip"] == "1.2.3.4"
