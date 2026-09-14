"""
Unit test for teams.py's gift_plan_from_treasury() — same TOCTOU race class
fixed elsewhere: the team treasury's balance was checked via a separate
SELECT (get_treasury()), then decremented via a separate UPDATE. A team can
have multiple leaders/moderators, so two of them gifting a plan from the
shared treasury near-simultaneously could both pass the check against the
same not-yet-decremented balance. Fixed with the atomic
UPDATE ... WHERE balance >= cost ... RETURNING pattern.
"""
import sqlite3

import pytest

import db as db_module
import teams


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_teams.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, plan TEXT DEFAULT 'free', plan_expires_at TEXT);
        CREATE TABLE teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT, custom_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
            leader_id INTEGER NOT NULL, description TEXT DEFAULT '', is_open INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'active', next_billing_at TEXT, tax_free_until TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT, team_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member', joined_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(team_id, user_id)
        );
        CREATE TABLE team_treasury (
            team_id INTEGER PRIMARY KEY, balance INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE team_treasury_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, team_id INTEGER NOT NULL, user_id INTEGER,
            direction TEXT NOT NULL, amount INTEGER NOT NULL, reason TEXT NOT NULL DEFAULT '',
            note TEXT DEFAULT '', created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            title TEXT, body TEXT, type TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users (id) VALUES (1), (2);
        INSERT INTO teams (id, custom_id, name, leader_id) VALUES (1, '00001', 'Test Team', 1);
        INSERT INTO team_members (team_id, user_id, role) VALUES (1, 1, 'leader');
        INSERT INTO team_members (team_id, user_id, role) VALUES (1, 2, 'member');
        INSERT INTO team_treasury (team_id, balance) VALUES (1, 500);
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(db_module, "USE_POSTGRES", False)
    monkeypatch.setitem(flask_app_module.app.config, "DB_PATH", test_db_path)
    monkeypatch.setitem(flask_app_module.app.config, "TESTING", True)
    monkeypatch.setattr(teams, "get_price", lambda key: 500)
    yield flask_app_module.app


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield


def test_gift_plan_success(ctx):
    ok, msg = teams.gift_plan_from_treasury(1, 2, "pro")
    assert ok is True
    assert teams.get_treasury(1)["balance"] == 0
    user = db_module.query_one("SELECT plan FROM users WHERE id=2")
    assert user["plan"] == "pro"


def test_gift_plan_insufficient_treasury_leaves_state_unchanged(ctx, monkeypatch):
    monkeypatch.setattr(teams, "get_price", lambda key: 9999)
    ok, msg = teams.gift_plan_from_treasury(1, 2, "pro")
    assert ok is False
    assert "yetarli" in msg
    assert teams.get_treasury(1)["balance"] == 500
    user = db_module.query_one("SELECT plan FROM users WHERE id=2")
    assert user["plan"] == "free"


def test_gift_plan_rejects_non_leader(ctx):
    ok, msg = teams.gift_plan_from_treasury(2, 1, "pro")  # user 2 is a plain member
    assert ok is False
    assert teams.get_treasury(1)["balance"] == 500
