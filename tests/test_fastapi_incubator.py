from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.incubator.entities import IncubatorIdea

client = TestClient(app)


class _FakeRepo:
    def __init__(self, plan, ideas=None):
        self._plan = plan
        self._ideas = ideas or []

    def get_user_plan(self, user_id):
        return self._plan

    def list_ideas(self, viewer_user_id):
        return self._ideas


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.incubator as incubator_module
    incubator_module.SqlAlchemyIncubatorRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/incubator")
    assert resp.status_code == 401


def test_non_hacker_plan_rejected():
    _override(_FakeRepo(plan="free"))
    resp = client.get("/api/v2/incubator")
    assert resp.status_code == 403


def test_hacker_plan_sees_ideas_with_vote_status():
    idea = IncubatorIdea(id=1, title="AI Tutor", description="Shaxsiy AI o'qituvchi",
                          stage="mvp", created_at="2026-01-01", ism="Ali", familiya="Valiyev",
                          vote_count=12, voted_by_me=True)
    _override(_FakeRepo(plan="hacker", ideas=[idea]))
    resp = client.get("/api/v2/incubator")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["vote_count"] == 12
    assert body[0]["voted_by_me"] is True
