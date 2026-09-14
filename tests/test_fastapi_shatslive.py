from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.shatslive.entities import LiveStream

client = TestClient(app)


class _FakeRepo:
    def __init__(self, plan, streams=None):
        self._plan = plan
        self._streams = streams or []

    def get_user_plan(self, user_id):
        return self._plan

    def list_streams(self, limit):
        return self._streams


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.shatslive as shatslive_module
    shatslive_module.SqlAlchemyShatsLiveRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/shats-live")
    assert resp.status_code == 401


def test_non_hacker_plan_rejected():
    _override(_FakeRepo(plan="free"))
    resp = client.get("/api/v2/shats-live")
    assert resp.status_code == 403


def test_hacker_plan_sees_streams():
    stream = LiveStream(id=1, title="CTF Workshop", description="Live pentest demo",
                         scheduled_at="2026-02-01 18:00:00", status="live", stream_url="https://x.test/live",
                         created_at="2026-01-01", host_ism="Ali", host_familiya="Valiyev")
    _override(_FakeRepo(plan="hacker", streams=[stream]))
    resp = client.get("/api/v2/shats-live")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["status"] == "live"
