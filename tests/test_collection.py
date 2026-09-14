"""
Unit tests for collection.py's open_mystery_chest() and
redeem_keys_for_statuette() — same TOCTOU race class as chests.py's ticket/
key functions: chest_tickets_mystery and chest_keys were each checked via a
separate SELECT in Python, then decremented via a separate UPDATE. Fixed
with the same atomic UPDATE ... WHERE col >= amount ... RETURNING pattern.
"""
import sqlite3

import pytest

import db as db_module
import collection


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_collection.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            chest_tickets_mystery INTEGER NOT NULL DEFAULT 0,
            chest_keys INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE user_collection (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, level INTEGER NOT NULL,
            unlocked_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, level)
        );
        CREATE TABLE chest_open_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chest_type TEXT,
            reward_type TEXT, reward_value TEXT, keys_won INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            title TEXT, body TEXT, type TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users (id, chest_tickets_mystery, chest_keys) VALUES (1, 1, 50);
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


def _get(col):
    return db_module.query_one(f"SELECT {col} FROM users WHERE id=1")[col]


def test_open_mystery_chest_success_decrements_ticket(ctx):
    result = collection.open_mystery_chest(1)
    assert result["ok"] is True
    assert _get("chest_tickets_mystery") == 0


def test_open_mystery_chest_rejects_when_no_tickets(ctx):
    collection.open_mystery_chest(1)  # spend the only ticket
    result = collection.open_mystery_chest(1)
    assert result["ok"] is False
    assert _get("chest_tickets_mystery") == 0


def test_redeem_keys_success_decrements_keys(ctx):
    result = collection.redeem_keys_for_statuette(1)
    assert result["ok"] is True
    assert _get("chest_keys") == 0  # 50 - KEY_REDEEM_COST(50)


def test_redeem_keys_rejects_when_insufficient(ctx):
    collection.redeem_keys_for_statuette(1)  # spend all 50 keys
    result = collection.redeem_keys_for_statuette(1)
    assert result["ok"] is False
    assert _get("chest_keys") == 0  # unchanged by the failed attempt
