"""
Phase 1 proof: FastAPI + legacy Flask coexistence, and the sandbox slice.

Run with:
    ./.venv/bin/pytest tests/test_fastapi_sandbox.py -v
"""
from fastapi.testclient import TestClient

from fastapi_app.main import app

client = TestClient(app)


def test_legacy_flask_routes_still_work_through_the_wsgi_mount():
    resp = client.get("/login")
    assert resp.status_code == 200


def test_sandbox_languages_list():
    resp = client.get("/api/v2/sandbox/languages")
    assert resp.status_code == 200
    assert "python" in resp.json()


def test_sandbox_runs_real_python_code():
    resp = client.post("/api/v2/sandbox/run", json={"language": "python", "code": "print(2 + 2)"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["output"].strip() == "4"


def test_sandbox_rejects_unsupported_language_gracefully():
    resp = client.post("/api/v2/sandbox/run", json={"language": "cobol", "code": "DISPLAY 'hi'"})
    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_terminal_clear_command():
    resp = client.post(
        "/api/v2/sandbox/terminal/execute",
        json={"direction_slug": "python", "command": "clear"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["cleared"] is True
