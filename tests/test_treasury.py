"""
Unit tests for treasury.py's issue_coins_to_user() — same TOCTOU race class
as coins.spend_coins() and chests.py's ticket/key functions, but on the
treasury fund's own balance: it was checked via a separate SELECT
(get_fund_balance()) then decremented via a separate UPDATE. Two treasury
staff issuing coins near-simultaneously when the fund is nearly depleted
could both pass the check and both deduct, driving the fund negative.
Fixed with the same atomic UPDATE ... WHERE balance >= amount ...
RETURNING pattern.
"""
import sqlite3

import pytest

import db as db_module
import treasury


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_treasury.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, code_balance INTEGER NOT NULL DEFAULT 0,
            is_blocked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE code_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL, reason TEXT NOT NULL DEFAULT '',
            ref_id INTEGER, created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE treasury_fund (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            balance INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE treasury_fund_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, direction TEXT NOT NULL,
            amount INTEGER NOT NULL, reason TEXT NOT NULL DEFAULT '',
            user_id INTEGER, treasury_account_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            title TEXT, body TEXT, type TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users (id, code_balance, is_blocked) VALUES (1, 0, 0);
        INSERT INTO users (id, code_balance, is_blocked) VALUES (2, 0, 1);
        INSERT INTO treasury_fund (id, balance) VALUES (1, 1000);
        """
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(db_module, "USE_POSTGRES", False)
    monkeypatch.setitem(flask_app_module.app.config, "DB_PATH", test_db_path)
    monkeypatch.setitem(flask_app_module.app.config, "TESTING", True)
    yield flask_app_module.app


@pytest.fixture()
def ctx(app):
    with app.app_context():
        yield


def test_issue_success(ctx):
    ok, msg = treasury.issue_coins_to_user(1, 1, 300)
    assert ok is True
    assert treasury.get_fund_balance() == 700
    assert db_module.query_one("SELECT code_balance FROM users WHERE id=1")["code_balance"] == 300


def test_issue_insufficient_fund_balance_leaves_state_unchanged(ctx):
    ok, msg = treasury.issue_coins_to_user(1, 1, 9999)
    assert ok is False
    assert "yetarli" in msg
    assert treasury.get_fund_balance() == 1000
    assert db_module.query_one("SELECT code_balance FROM users WHERE id=1")["code_balance"] == 0


def test_issue_rejects_blocked_user(ctx):
    ok, msg = treasury.issue_coins_to_user(1, 2, 100)
    assert ok is False
    assert treasury.get_fund_balance() == 1000


def test_issue_rejects_non_positive_amount(ctx):
    ok, msg = treasury.issue_coins_to_user(1, 1, 0)
    assert ok is False
    ok, msg = treasury.issue_coins_to_user(1, 1, -5)
    assert ok is False
    assert treasury.get_fund_balance() == 1000


def test_issue_exact_fund_balance(ctx):
    ok, msg = treasury.issue_coins_to_user(1, 1, 1000)
    assert ok is True
    assert treasury.get_fund_balance() == 0
