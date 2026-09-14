from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.startups.entities import Startup

client = TestClient(app)


class _FakeRepo:
    def __init__(self, items):
        self._items = items

    def list_approved(self, viewer_user_id, limit):
        return self._items


def teardown_function():
    app.dependency_overrides.clear()


def test_requires_auth():
    resp = client.get("/api/v2/startups")
    assert resp.status_code == 401


def test_lists_approved_startups():
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.startups as startups_module
    startups_module.SqlAlchemyStartupsRepository = lambda db: _FakeRepo(
        [
            Startup(id=1, name="CodeHelper", description="AI yordamchi", image_path=None,
                    link_url="https://example.com", category="ai", view_count=42,
                    created_at="2026-01-01", in_auction=0, needs_help=1,
                    author_id=1, author_ism="Ali", author_familiya="Valiyev",
                    author_avatar=None, like_count=3, liked_by_me=True),
        ]
    )

    resp = client.get("/api/v2/startups")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["like_count"] == 3
    assert body[0]["liked_by_me"] is True
