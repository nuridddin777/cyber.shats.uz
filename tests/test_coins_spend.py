"""
Unit tests for coins.py's spend/add/refund — the highest-stakes logic in
the app (real money). Uses a throwaway local SQLite file with just the two
tables these functions touch; coins.py's logic is DB-engine-agnostic via
db.py, so this validates correctness. The specific race-condition fix in
spend_coins() (atomic UPDATE...WHERE...RETURNING) was additionally verified
by hand against real production Postgres with two real concurrent threads —
SQLite serializes all writes globally regardless, so it can't exercise the
race itself, only the surrounding logic.
"""
import os
import sqlite3

import pytest

import db as db_module
import coins


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_coins.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, code_balance INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE code_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            ref_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users (id, code_balance) VALUES (1, 100);
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


def test_spend_success(ctx):
    ok, msg = coins.spend_coins(1, 30, "test_purchase")
    assert ok is True
    assert coins.get_balance(1) == 70
    txns = coins.get_transactions(1, 10)
    assert txns[0]["amount"] == -30
    assert txns[0]["reason"] == "test_purchase"


def test_spend_insufficient_balance_leaves_balance_unchanged(ctx):
    ok, msg = coins.spend_coins(1, 999, "too_much")
    assert ok is False
    assert "Yetarli" in msg
    assert coins.get_balance(1) == 100
    assert coins.get_transactions(1, 10) == []


def test_spend_rejects_non_positive_amount(ctx):
    ok, msg = coins.spend_coins(1, 0, "zero")
    assert ok is False
    ok, msg = coins.spend_coins(1, -5, "negative")
    assert ok is False
    assert coins.get_balance(1) == 100


def test_add_then_spend_exact_balance(ctx):
    coins.add_coins(1, 50, "bonus")
    assert coins.get_balance(1) == 150
    ok, _ = coins.spend_coins(1, 150, "spend_all")
    assert ok is True
    assert coins.get_balance(1) == 0


def test_refund_restores_balance(ctx):
    coins.spend_coins(1, 40, "purchase")
    assert coins.get_balance(1) == 60
    coins.refund_coins(1, 40, "purchase")
    assert coins.get_balance(1) == 100
    txns = coins.get_transactions(1, 10)
    assert txns[0]["reason"] == "refund_purchase"
    assert txns[0]["amount"] == 40
