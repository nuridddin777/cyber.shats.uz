"""
Unit tests for coins.py's AI daily-usage functions — same TOCTOU race class
fixed elsewhere:

- ensure_ai_access_general(): the free daily quota was checked via SELECT,
  then incremented via a separate, unconditional UPSERT — two near-
  simultaneous AI requests from a free user could both pass the check and
  both increment, letting the user exceed their free daily limit (a real
  cost, since each request hits an external AI API).
- buy_ai_daily_boost(): the current boost tier was checked via SELECT,
  THEN coins were spent, THEN boost_multiplier was set unconditionally —
  two near-simultaneous purchases could both pass the check and both pay,
  but only one boost value would end up stored (double payment, single
  benefit).

Both fixed with an atomic UPSERT guarded by a WHERE clause + RETURNING.
"""
import sqlite3

import pytest

import db as db_module
import coins


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_ai_usage.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY, role TEXT DEFAULT 'student', plan TEXT DEFAULT 'free',
            code_balance INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE ai_daily_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, usage_date TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0, boost_multiplier INTEGER DEFAULT 1,
            UNIQUE(user_id, usage_date)
        );
        CREATE TABLE code_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL, reason TEXT NOT NULL DEFAULT '',
            ref_id INTEGER, created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users (id, role, plan, code_balance) VALUES (1, 'student', 'free', 100);
        INSERT INTO users (id, role, plan, code_balance) VALUES (2, 'admin', 'free', 0);
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


def test_free_user_gets_exactly_three_then_rejected(ctx):
    for _ in range(3):
        ok, msg = coins.ensure_ai_access_general(1)
        assert ok is True
    ok, msg = coins.ensure_ai_access_general(1)
    assert ok is False
    assert "limit" in msg.lower() or "tugadi" in msg


def test_admin_is_unlimited(ctx):
    for _ in range(10):
        ok, msg = coins.ensure_ai_access_general(2)
        assert ok is True
        assert msg == "unlimited"


def test_buy_boost_success_raises_limit_and_charges_once(ctx):
    ok, msg = coins.buy_ai_daily_boost(1, 2)
    assert ok is True
    assert coins.get_balance(1) == 95  # 100 - AI_BOOST_2X_PRICE(5)
    row = db_module.query_one("SELECT boost_multiplier FROM ai_daily_usage WHERE user_id=1 AND usage_date=?",
                              (__import__("datetime").date.today().isoformat(),))
    assert row["boost_multiplier"] == 2


def test_buy_boost_rejects_when_already_at_or_above_multiplier(ctx):
    coins.buy_ai_daily_boost(1, 5)  # jumps straight to 5x
    balance_after_first = coins.get_balance(1)
    ok, msg = coins.buy_ai_daily_boost(1, 2)  # 2x is not > current 5x
    assert ok is False
    assert coins.get_balance(1) == balance_after_first  # not charged again


def test_buy_boost_insufficient_balance_leaves_multiplier_unclaimed(ctx):
    db_module.execute("UPDATE users SET code_balance=0 WHERE id=1")
    ok, msg = coins.buy_ai_daily_boost(1, 2)
    assert ok is False
    row = db_module.query_one("SELECT boost_multiplier FROM ai_daily_usage WHERE user_id=1 AND usage_date=?",
                              (__import__("datetime").date.today().isoformat(),))
    assert row is None or row["boost_multiplier"] in (None, 1)  # claim was rolled back
