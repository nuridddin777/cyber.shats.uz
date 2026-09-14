from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.friends.entities import Friend

client = TestClient(app)


class _FakeRepo:
    def __init__(self, items):
        self._items = items

    def list_friends(self, user_id):
        return self._items


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_auth():
    resp = client.get("/api/v2/friends")
    assert resp.status_code == 401


def test_lists_friends():
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.friends as friends_module
    friends_module.SqlAlchemyFriendsRepository = lambda db: _FakeRepo(
        [Friend(id=2, ism="Ali", familiya="V", custom_id="123", avatar_path=None, level=3, last_login_date="2026-08-26")]
    )

    resp = client.get("/api/v2/friends")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["ism"] == "Ali"
