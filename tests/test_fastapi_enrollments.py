from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.enrollments.entities import Enrollment

client = TestClient(app)


class _FakeRepo:
    def __init__(self, items):
        self._items = items

    def list_for_user(self, user_id):
        return self._items


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_auth():
    resp = client.get("/api/v2/enrollments")
    assert resp.status_code == 401


def test_lists_own_enrollments():
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.enrollments as enr_module
    enr_module.SqlAlchemyEnrollmentsRepository = lambda db: _FakeRepo(
        [Enrollment(id=1, course_id=5, title="Python", slug="python", icon="code",
                    progress_percent=40, started_at="2026-01-01", completed_at=None)]
    )

    resp = client.get("/api/v2/enrollments")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["progress_percent"] == 40
