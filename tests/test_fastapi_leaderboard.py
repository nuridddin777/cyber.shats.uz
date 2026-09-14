from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.leaderboard.entities import LeaderboardEntry

client = TestClient(app)


class _FakeRepo:
    def __init__(self, xp_board=None, code_board=None, xp_rank=0, code_rank=0):
        self._xp_board = xp_board or []
        self._code_board = code_board or []
        self._xp_rank = xp_rank
        self._code_rank = code_rank

    def list_xp_board(self, limit):
        return self._xp_board

    def list_code_board(self, limit):
        return self._code_board

    def my_xp_rank(self, user_id):
        return self._xp_rank

    def my_code_rank(self, user_id):
        return self._code_rank


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.leaderboard as lb_module
    lb_module.SqlAlchemyLeaderboardRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/leaderboard")
    assert resp.status_code == 401


def test_xp_board_default():
    entry = LeaderboardEntry(id=1, ism="Ali", familiya="Valiyev", avatar=None, level=5,
                              plan="free", code_balance=100, total_score=500,
                              courses_done=3, rank_position=1)
    _override(_FakeRepo(xp_board=[entry], xp_rank=7))

    resp = client.get("/api/v2/leaderboard")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["leaders"]) == 1
    assert body["leaders"][0]["total_score"] == 500
    assert body["my_rank"] == 7


def test_code_board():
    entry = LeaderboardEntry(id=2, ism="Vali", familiya="Aliyev", avatar=None, level=3,
                              plan="free", code_balance=900, total_score=900,
                              courses_done=0, rank_position=0)
    _override(_FakeRepo(code_board=[entry], code_rank=2))

    resp = client.get("/api/v2/leaderboard?type=code")
    assert resp.status_code == 200
    body = resp.json()
    assert body["leaders"][0]["code_balance"] == 900
    assert body["my_rank"] == 2


def test_rejects_invalid_type():
    _override(_FakeRepo())
    resp = client.get("/api/v2/leaderboard?type=bogus")
    assert resp.status_code == 422
