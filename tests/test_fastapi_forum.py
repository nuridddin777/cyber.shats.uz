from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.forum.entities import ForumCategory, ForumPost

client = TestClient(app)


class _FakeRepo:
    def __init__(self, posts=None, categories=None):
        self._posts = posts or []
        self._categories = categories or []

    def list_posts(self, category, limit):
        if category:
            return [p for p in self._posts if p.category == category]
        return self._posts

    def list_categories(self):
        return self._categories


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.forum as forum_module
    forum_module.SqlAlchemyForumRepository = lambda db: repo


def test_posts_require_auth():
    resp = client.get("/api/v2/forum/posts")
    assert resp.status_code == 401


def test_lists_posts():
    posts = [
        ForumPost(id=1, title="Salom", body="birinchi post", category="umumiy", views=5,
                  replies_count=2, created_at="2026-01-01", author_id=1, author_ism="Ali",
                  author_familiya="Valiyev", author_avatar=None),
        ForumPost(id=2, title="CTF", body="ctf haqida", category="ctf", views=1,
                  replies_count=0, created_at="2026-01-02", author_id=2, author_ism="Vali",
                  author_familiya="Aliyev", author_avatar="a.png"),
    ]
    _override(_FakeRepo(posts=posts))

    resp = client.get("/api/v2/forum/posts")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["title"] == "Salom"


def test_filters_posts_by_category():
    posts = [
        ForumPost(id=1, title="A", body="b", category="umumiy", views=0, replies_count=0,
                  created_at="2026-01-01", author_id=1, author_ism="X", author_familiya="Y",
                  author_avatar=None),
        ForumPost(id=2, title="B", body="c", category="ctf", views=0, replies_count=0,
                  created_at="2026-01-01", author_id=1, author_ism="X", author_familiya="Y",
                  author_avatar=None),
    ]
    _override(_FakeRepo(posts=posts))

    resp = client.get("/api/v2/forum/posts?category=ctf")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["category"] == "ctf"


def test_lists_categories():
    _override(_FakeRepo(categories=[ForumCategory(category="umumiy", post_count=10)]))
    resp = client.get("/api/v2/forum/categories")
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["category"] == "umumiy"
    assert body[0]["post_count"] == 10
