from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.career.entities import JobListing

client = TestClient(app)


class _FakeRepo:
    def __init__(self, plan, jobs=None):
        self._plan = plan
        self._jobs = jobs or []

    def get_user_plan(self, user_id):
        return self._plan

    def list_open(self, viewer_user_id):
        return self._jobs


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.career as career_module
    career_module.SqlAlchemyCareerRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/career")
    assert resp.status_code == 401


def test_non_hacker_plan_rejected():
    _override(_FakeRepo(plan="free"))
    resp = client.get("/api/v2/career")
    assert resp.status_code == 403


def test_hacker_plan_sees_jobs_with_applied_flag():
    job = JobListing(id=1, title="Backend Developer", company="Cyber Shats",
                      description="Python/FastAPI", location="Masofaviy", status="open",
                      created_at="2026-01-01", already_applied=True)
    _override(_FakeRepo(plan="hacker", jobs=[job]))
    resp = client.get("/api/v2/career")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["already_applied"] is True
