"""
Tests for /api/v2/coins/* — read-only. Uses dependency overrides, no real
Postgres connection needed.
"""
from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.coins.entities import CoinTransaction, LeaderboardEntry

client = TestClient(app)


class _FakeRepo:
    def __init__(self, balance=None, transactions=None, leaderboard=None):
        self._balance = balance
        self._transactions = transactions or []
        self._leaderboard = leaderboard or []

    def get_balance(self, user_id):
        return self._balance

    def get_transactions(self, user_id, limit):
        return self._transactions[:limit]

    def get_leaderboard(self, limit):
        return self._leaderboard[:limit]


def _use_repo(repo):
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    import fastapi_app.interfaces.api.routers.coins as coins_module
    coins_module.SqlAlchemyCoinsRepository = lambda db: repo


def teardown_function():
    app.dependency_overrides.clear()


def test_balance_requires_auth():
    resp = client.get("/api/v2/coins/balance")
    assert resp.status_code == 401


def test_balance_returns_amount():
    _use_repo(_FakeRepo(balance=1500))
    app.dependency_overrides[get_current_user_id] = lambda: 1

    resp = client.get("/api/v2/coins/balance")
    assert resp.status_code == 200
    assert resp.json()["balance"] == 1500


def test_balance_404_for_unknown_user():
    _use_repo(_FakeRepo(balance=None))
    app.dependency_overrides[get_current_user_id] = lambda: 999

    resp = client.get("/api/v2/coins/balance")
    assert resp.status_code == 404


def test_transactions_list():
    txns = [
        CoinTransaction(id=2, amount=-100, reason="buy_course", ref_id=5, created_at="2026-01-01 00:00:00"),
        CoinTransaction(id=1, amount=500, reason="course_reward", ref_id=None, created_at="2026-01-01 00:00:00"),
    ]
    _use_repo(_FakeRepo(transactions=txns))
    app.dependency_overrides[get_current_user_id] = lambda: 1

    resp = client.get("/api/v2/coins/transactions")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["id"] == 2
    assert body[0]["amount"] == -100


def test_leaderboard_is_public():
    entries = [
        LeaderboardEntry(id=1, ism="Ali", familiya="V", level=5, code_balance=1000, total_score=900, courses_done=3),
    ]
    _use_repo(_FakeRepo(leaderboard=entries))

    resp = client.get("/api/v2/coins/leaderboard")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["total_score"] == 900
