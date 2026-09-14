"""
Tests for /api/v2/me — the first FastAPI slice that needs a logged-in user.
Uses FastAPI's dependency override so no real Postgres connection is needed.
"""
from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.users.entities import UserProfile

client = TestClient(app)


class _FakeRepo:
    def __init__(self, profile):
        self._profile = profile

    def get_profile(self, user_id):
        return self._profile if self._profile and self._profile.id == user_id else None


def _override_db_with(profile):
    def _get_db():
        yield None  # unused directly; the router builds a repo from this session

    app.dependency_overrides[get_db_session] = _get_db
    # SqlAlchemyUserRepository is constructed inside the route with this
    # session; patch it out entirely by overriding at the router-usage level
    # instead is more invasive than needed here — simplest is to monkeypatch
    # the repository class the route imports.
    import fastapi_app.interfaces.api.routers.me as me_module
    me_module.SqlAlchemyUserRepository = lambda db: _FakeRepo(profile)


def teardown_function():
    app.dependency_overrides.clear()


def test_me_requires_auth():
    resp = client.get("/api/v2/me")
    assert resp.status_code == 401


def test_me_returns_profile_for_logged_in_user():
    profile = UserProfile(
        id=42, ism="Ali", familiya="Valiyev", email="ali@example.com",
        role="student", plan="free", xp=10, level=2, code_balance=500, custom_id="12345",
    )
    _override_db_with(profile)
    app.dependency_overrides[get_current_user_id] = lambda: 42

    resp = client.get("/api/v2/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 42
    assert body["ism"] == "Ali"
    assert body["code_balance"] == 500


def test_me_returns_404_for_unknown_user():
    _override_db_with(None)
    app.dependency_overrides[get_current_user_id] = lambda: 999

    resp = client.get("/api/v2/me")
    assert resp.status_code == 404
