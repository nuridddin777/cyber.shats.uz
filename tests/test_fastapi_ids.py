from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_db_session
from fastapi_app.domain.ids.entities import PremiumId

client = TestClient(app)


class _FakeRepo:
    def __init__(self, items):
        self._items = items

    def list_marketplace(self):
        return self._items


def teardown_function():
    app.dependency_overrides.clear()


def test_marketplace_is_public_and_lists_items():
    def _get_db():
        yield None

    app.dependency_overrides[get_db_session] = _get_db
    import fastapi_app.interfaces.api.routers.ids as ids_module
    ids_module.SqlAlchemyIdsRepository = lambda db: _FakeRepo(
        [PremiumId(id=1, custom_id="1234567", id_type="custom", base_price=50000, status="available", owner_user_id=None)]
    )

    resp = client.get("/api/v2/ids/marketplace")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["custom_id"] == "1234567"
