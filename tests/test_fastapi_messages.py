from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session

client = TestClient(app)


class _FakeRepo:
    def __init__(self, unread=0):
        self._unread = unread

    def count_unread(self, user_id):
        return self._unread


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_auth():
    resp = client.get("/api/v2/messages/unread-count")
    assert resp.status_code == 401


def test_unread_count():
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.messages as messages_module
    messages_module.SqlAlchemyMessagesRepository = lambda db: _FakeRepo(unread=3)

    resp = client.get("/api/v2/messages/unread-count")
    assert resp.status_code == 200
    assert resp.json()["count"] == 3
