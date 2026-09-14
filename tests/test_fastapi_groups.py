from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.groups.entities import Group

client = TestClient(app)


class _FakeRepo:
    def __init__(self, items):
        self._items = items

    def list_all(self, viewer_user_id, limit):
        return self._items


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_auth():
    resp = client.get("/api/v2/groups")
    assert resp.status_code == 401


def test_lists_groups_with_membership_flag():
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.groups as groups_module
    groups_module.SqlAlchemyGroupsRepository = lambda db: _FakeRepo(
        [
            Group(id=1, name="CTF Club", description="", avatar=None, public_id="ctf1",
                  is_public=1, member_count=42, created_at="2026-01-01", owner_id=2,
                  owner_ism="Ali", owner_familiya="Valiyev", is_member=True, my_role="member"),
            Group(id=2, name="Not Joined", description="", avatar=None, public_id="nj",
                  is_public=1, member_count=5, created_at="2026-01-02", owner_id=3,
                  owner_ism="Vali", owner_familiya="Aliyev", is_member=False, my_role=None),
        ]
    )

    resp = client.get("/api/v2/groups")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["is_member"] is True and body[0]["my_role"] == "member"
    assert body[1]["is_member"] is False and body[1]["my_role"] is None
