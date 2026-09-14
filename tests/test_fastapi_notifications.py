from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.notifications.entities import Notification

client = TestClient(app)


class _FakeRepo:
    def __init__(self, items=None, unread=0):
        self._items = items or []
        self._unread = unread

    def list_for_user(self, user_id, limit):
        return self._items[:limit]

    def count_unread(self, user_id):
        return self._unread


def _use_repo(repo):
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    import fastapi_app.interfaces.api.routers.notifications as notif_module
    notif_module.SqlAlchemyNotificationsRepository = lambda db: repo


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_auth():
    resp = client.get("/api/v2/notifications")
    assert resp.status_code == 401


def test_lists_notifications():
    items = [Notification(id=1, title="Salom", body="Xush kelibsiz", type="info", is_read=0, created_at="2026-01-01")]
    _use_repo(_FakeRepo(items=items))
    app.dependency_overrides[get_current_user_id] = lambda: 1

    resp = client.get("/api/v2/notifications")
    assert resp.status_code == 200
    assert resp.json()[0]["title"] == "Salom"


def test_unread_count():
    _use_repo(_FakeRepo(unread=7))
    app.dependency_overrides[get_current_user_id] = lambda: 1

    resp = client.get("/api/v2/notifications/unread-count")
    assert resp.status_code == 200
    assert resp.json()["count"] == 7
