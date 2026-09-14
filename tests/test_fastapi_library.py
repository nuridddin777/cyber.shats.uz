from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.library.entities import Book, NewsItem

client = TestClient(app)


class _FakeRepo:
    def __init__(self, books=None, news=None):
        self._books = books or []
        self._news = news or []

    def list_books(self, category):
        if category:
            return [b for b in self._books if b.category == category]
        return self._books

    def list_news(self, category, limit):
        if category:
            return [n for n in self._news if n.category == category]
        return self._news


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.library as library_module
    library_module.SqlAlchemyLibraryRepository = lambda db: repo


def test_books_require_auth():
    resp = client.get("/api/v2/books")
    assert resp.status_code == 401


def test_news_require_auth():
    resp = client.get("/api/v2/news")
    assert resp.status_code == 401


def test_lists_books_filtered_by_category():
    books = [
        Book(id=1, title="Clean Code", type="pdf", size_label="4MB", category="dev", file_url="/f/1"),
        Book(id=2, title="CTF Guide", type="pdf", size_label="2MB", category="security", file_url="/f/2"),
    ]
    _override(_FakeRepo(books=books))

    resp = client.get("/api/v2/books?cat=security")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "CTF Guide"


def test_lists_news_unfiltered():
    news = [
        NewsItem(id=1, title="Update", summary="s", source="src", category="platform",
                 published_at="2026-01-01", url="/n/1"),
    ]
    _override(_FakeRepo(news=news))

    resp = client.get("/api/v2/news")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Update"
