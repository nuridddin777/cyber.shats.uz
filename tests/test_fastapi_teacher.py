from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.teacher.entities import TeacherChannel, TeacherGroup

client = TestClient(app)


class _FakeRepo:
    def __init__(self, is_teacher, groups=None, channels=None):
        self._is_teacher = is_teacher
        self._groups = groups or []
        self._channels = channels or []

    def is_teacher(self, user_id):
        return self._is_teacher

    def list_my_groups(self, user_id):
        return self._groups

    def list_my_channels(self, user_id):
        return self._channels


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.teacher as teacher_module
    teacher_module.SqlAlchemyTeacherRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/teacher")
    assert resp.status_code == 401


def test_non_teacher_rejected():
    _override(_FakeRepo(is_teacher=False))
    resp = client.get("/api/v2/teacher")
    assert resp.status_code == 403


def test_teacher_sees_dashboard():
    group = TeacherGroup(id=1, name="Python guruhi", created_at="2026-01-01")
    channel = TeacherChannel(id=1, name="Yangiliklar", subscriber_count=50, created_at="2026-01-01")
    _override(_FakeRepo(is_teacher=True, groups=[group], channels=[channel]))
    resp = client.get("/api/v2/teacher")
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_teacher"] is True
    assert body["my_groups"][0]["name"] == "Python guruhi"
    assert body["my_channels"][0]["subscriber_count"] == 50
