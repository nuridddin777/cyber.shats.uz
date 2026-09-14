from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.organization.entities import Organization, OrganizationPost

client = TestClient(app)


class _FakeRepo:
    def __init__(self, plan, org=None, posts=None, request_status=None):
        self._plan = plan
        self._org = org
        self._posts = posts or []
        self._request_status = request_status

    def get_user_plan(self, user_id):
        return self._plan

    def get_by_key(self, org_key):
        return self._org

    def list_posts(self, org_key, limit=20):
        return self._posts

    def get_my_latest_request_status(self, org_key, user_id):
        return self._request_status


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.organization as org_module
    org_module.SqlAlchemyOrganizationRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/organizations/mat")
    assert resp.status_code == 401


def test_non_hacker_plan_rejected():
    _override(_FakeRepo(plan="free"))
    resp = client.get("/api/v2/organizations/mat")
    assert resp.status_code == 403


def test_invalid_org_key_404():
    _override(_FakeRepo(plan="hacker"))
    resp = client.get("/api/v2/organizations/bogus")
    assert resp.status_code == 404


def test_valid_org_key_returns_page():
    org = Organization(id=1, org_key="mat", name="MAT", description="d",
                        stats_members=100, stats_projects=5, stats_years=3)
    post = OrganizationPost(id=1, title="Yangilik", content="matn", created_at="2026-01-01")
    _override(_FakeRepo(plan="hacker", org=org, posts=[post], request_status="pending"))
    resp = client.get("/api/v2/organizations/mat")
    assert resp.status_code == 200
    body = resp.json()
    assert body["org"]["name"] == "MAT"
    assert body["posts"][0]["title"] == "Yangilik"
    assert body["my_request_status"] == "pending"
