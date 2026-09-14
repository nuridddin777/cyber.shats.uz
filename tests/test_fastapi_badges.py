from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.badges.entities import Badge

client = TestClient(app)


class _FakeRepo:
    def __init__(self, items):
        self._items = items

    def list_for_user(self, user_id):
        return self._items


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_auth():
    resp = client.get("/api/v2/badges")
    assert resp.status_code == 401


def test_lists_all_badges_with_earned_status():
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.badges as badges_module
    badges_module.SqlAlchemyBadgesRepository = lambda db: _FakeRepo(
        [
            Badge(id=1, name="First Steps", icon="star", description="Complete your first test",
                  earned=True, earned_at="2026-01-01 10:00:00"),
            Badge(id=2, name="Marathon", icon="trophy", description="Complete 10 courses",
                  earned=False, earned_at=None),
        ]
    )

    resp = client.get("/api/v2/badges")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["earned"] is True
    assert body[1]["earned"] is False
    assert body[1]["earned_at"] is None
