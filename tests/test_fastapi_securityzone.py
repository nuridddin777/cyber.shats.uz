from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.domain.securityzone.entities import (
    BlacklistApp, ChecklistItem, GlossaryTerm, SecurityArticle, SecurityZoneOverview,
)

client = TestClient(app)


class _FakeRepo:
    def __init__(self, plan, overview=None):
        self._plan = plan
        self._overview = overview

    def get_user_plan(self, user_id):
        return self._plan

    def get_overview(self, user_id):
        return self._overview


def teardown_function():
    app.dependency_overrides.clear()


def _override(repo):
    def _get_db():
        yield None
    app.dependency_overrides[get_db_session] = _get_db
    app.dependency_overrides[get_current_user_id] = lambda: 1
    import fastapi_app.interfaces.api.routers.securityzone as sz_module
    sz_module.SqlAlchemySecurityZoneRepository = lambda db: repo


def test_requires_auth():
    resp = client.get("/api/v2/security-zone")
    assert resp.status_code == 401


def test_non_hacker_plan_rejected():
    _override(_FakeRepo(plan="free"))
    resp = client.get("/api/v2/security-zone")
    assert resp.status_code == 403


def test_hacker_plan_sees_overview():
    overview = SecurityZoneOverview(
        articles=[SecurityArticle(id=1, category="phishing", title="Fishing nima?",
                                   slug="fishing", summary="s", order_index=0)],
        glossary=[GlossaryTerm(id=1, term="VPN", definition="Virtual private network")],
        blacklist=[BlacklistApp(id=1, name="ShadyApp", reason="Malware tarqatadi")],
        checklist=[ChecklistItem(id=1, category="parol", text="Kuchli parol qo'ying", checked=True)],
        checklist_done=1, checklist_total=1, user_score=85, user_level="Ilg'or",
    )
    _override(_FakeRepo(plan="hacker", overview=overview))
    resp = client.get("/api/v2/security-zone")
    assert resp.status_code == 200
    body = resp.json()
    assert body["checklist_done"] == 1
    assert body["user_score"] == 85
    assert body["articles"][0]["title"] == "Fishing nima?"
