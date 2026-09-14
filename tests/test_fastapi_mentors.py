from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.mentors.entities import Mentor

client = TestClient(app)


class _FakeRepo:
    def __init__(self, plan, mentors=None):
        self._plan = plan
        self._mentors = mentors or []

    def get_user_plan(self, user_id):
        return self._plan

    def list_all(self):
        return self._mentors


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.mentors as mentors_module
    mentors_module.SqlAlchemyMentorsRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/mentors")
    assert resp.status_code == 401


def test_non_hacker_plan_rejected():
    _override(_FakeRepo(plan="free"))
    resp = client.get("/api/v2/mentors")
    assert resp.status_code == 403


def test_hacker_plan_sees_mentors():
    mentor = Mentor(user_id=2, skills="Python, Security", bio="10 yil tajriba", contact="@ali",
                     created_at="2026-01-01", ism="Ali", familiya="Valiyev", custom_id="12345")
    _override(_FakeRepo(plan="hacker", mentors=[mentor]))
    resp = client.get("/api/v2/mentors")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["skills"] == "Python, Security"
