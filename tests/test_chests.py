"""
Unit tests for chests.py's ticket/key-consuming functions. All four had the
same TOCTOU race as coins.spend_coins(): a separate SELECT-then-check in
Python followed by a separate UPDATE, so two near-simultaneous calls (double
click, two tabs) could both pass the check against the same not-yet-
decremented balance and both proceed — letting one ticket/key open two
chests, or a gift exceed what the sender actually had. Fixed with the same
atomic UPDATE ... WHERE col >= amount ... RETURNING pattern used in
coins.spend_coins() and payment_gateway.mark_paid().
"""
import sqlite3

import pytest

import db as db_module
import chests
import ids as ids_module


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_chests.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            ism TEXT DEFAULT '', familiya TEXT DEFAULT '',
            chest_tickets_tariff INTEGER NOT NULL DEFAULT 0,
            chest_tickets_id INTEGER NOT NULL DEFAULT 0,
            tariff_chest_opens INTEGER NOT NULL DEFAULT 0,
            chest_keys INTEGER NOT NULL DEFAULT 0,
            checkmark_badge TEXT,
            exclusive_theme TEXT,
            plan TEXT DEFAULT 'free',
            plan_expires_at TEXT
        );
        CREATE TABLE checkmark_shop (
            badge_key TEXT PRIMARY KEY, label TEXT, price_code INTEGER,
            price_keys INTEGER, is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE chest_open_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, chest_type TEXT,
            reward_type TEXT, reward_value TEXT, keys_won INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE user_id_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, custom_id TEXT,
            obtained_via TEXT, status TEXT
        );
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            title TEXT, body TEXT, type TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users (id, ism, familiya, chest_tickets_tariff, chest_tickets_id, chest_keys)
            VALUES (1, 'Test', 'User', 1, 1, 10);
        INSERT INTO users (id, ism, familiya) VALUES (2, 'Friend', 'User');
        INSERT INTO checkmark_shop (badge_key, label, price_code, price_keys, is_active)
            VALUES ('star', 'Star', 100, 5, 1);
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


def _get(col, user_id=1):
    return db_module.query_one(f"SELECT {col} FROM users WHERE id=?", (user_id,))[col]


def test_open_tariff_chest_success_decrements_ticket(ctx):
    result = chests.open_tariff_chest(1)
    assert result["ok"] is True
    assert _get("chest_tickets_tariff") == 0
    assert _get("tariff_chest_opens") == 1


def test_open_tariff_chest_rejects_when_no_tickets(ctx):
    chests.open_tariff_chest(1)  # spend the only ticket
    result = chests.open_tariff_chest(1)
    assert result["ok"] is False
    assert _get("chest_tickets_tariff") == 0
    assert _get("tariff_chest_opens") == 1  # unchanged by the failed attempt


def test_open_id_chest_success_decrements_ticket(ctx, monkeypatch):
    monkeypatch.setattr(
        ids_module, "generate_random_id_offer",
        lambda: {"custom_id": "1234567", "price": 100, "score": 1}
    )
    result = chests.open_id_chest(1)
    assert result["ok"] is True
    assert _get("chest_tickets_id") == 0


def test_open_id_chest_rejects_when_no_tickets(ctx, monkeypatch):
    monkeypatch.setattr(
        ids_module, "generate_random_id_offer",
        lambda: {"custom_id": "1234567", "price": 100, "score": 1}
    )
    chests.open_id_chest(1)  # spend the only ticket
    result = chests.open_id_chest(1)
    assert result["ok"] is False
    assert _get("chest_tickets_id") == 0


def test_buy_checkmark_with_keys_success(ctx):
    ok, msg = chests.buy_checkmark(1, "star", "keys")
    assert ok is True
    assert _get("chest_keys") == 5
    assert _get("checkmark_badge") == "star"


def test_buy_checkmark_with_keys_insufficient(ctx):
    ok, msg = chests.buy_checkmark(1, "star", "keys")  # 10 -> 5
    ok2, msg2 = chests.buy_checkmark(1, "star", "keys")  # needs 5 more, has 5 -> still ok
    ok3, msg3 = chests.buy_checkmark(1, "star", "keys")  # needs 5 more, has 0 -> fails
    assert (ok, ok2, ok3) == (True, True, False)
    assert _get("chest_keys") == 0  # not driven negative by the failed attempt


def test_gift_tickets_moves_between_friends(ctx, monkeypatch):
    import friends as friends_mod
    monkeypatch.setattr(friends_mod, "get_friendship_status", lambda a, b: "friends")
    ok, msg = chests.gift_tickets(1, 2, "tariff", 1)
    assert ok is True
    assert _get("chest_tickets_tariff", 1) == 0
    assert _get("chest_tickets_tariff", 2) == 1


def test_gift_tickets_rejects_when_sender_lacks_tickets(ctx, monkeypatch):
    import friends as friends_mod
    monkeypatch.setattr(friends_mod, "get_friendship_status", lambda a, b: "friends")
    ok, msg = chests.gift_tickets(1, 2, "tariff", 5)  # sender only has 1
    assert ok is False
    assert _get("chest_tickets_tariff", 1) == 1  # unchanged
    assert _get("chest_tickets_tariff", 2) == 0
