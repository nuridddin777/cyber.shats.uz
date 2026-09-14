from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.freelance.entities import FreelanceGig

client = TestClient(app)


class _FakeRepo:
    def __init__(self, plan, gigs=None):
        self._plan = plan
        self._gigs = gigs or []

    def get_user_plan(self, user_id):
        return self._plan

    def list_open(self, limit):
        return self._gigs


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.freelance as freelance_module
    freelance_module.SqlAlchemyFreelanceRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/freelance")
    assert resp.status_code == 401


def test_non_hacker_plan_rejected():
    _override(_FakeRepo(plan="free"))
    resp = client.get("/api/v2/freelance")
    assert resp.status_code == 403


def test_hacker_plan_sees_open_gigs():
    gig = FreelanceGig(id=1, gig_type="offer", title="Web sayt yasab beraman",
                        description="React + FastAPI", price_code=500, status="open",
                        created_at="2026-01-01", ism="Ali", familiya="Valiyev", custom_id="12345")
    _override(_FakeRepo(plan="hacker", gigs=[gig]))
    resp = client.get("/api/v2/freelance")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Web sayt yasab beraman"
