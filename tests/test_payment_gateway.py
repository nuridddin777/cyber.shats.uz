"""
Unit tests for payment_gateway.py's mark_paid() — the auto-credit path that
runs from real bank webhooks (Click/Payme/Uzum). MUHIM: providers are known
to retry webhook delivery, so mark_paid() must be idempotent even when two
calls for the same merchant_trans_id land back-to-back. The fix (atomic
UPDATE payment_transactions ... WHERE status != 'paid' RETURNING ...)
mirrors the same race-condition pattern already fixed in coins.spend_coins().
"""
import sqlite3

import pytest

import db as db_module
import payment_gateway


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_payments.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, code_balance INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE payment_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_txn_id TEXT,
            merchant_trans_id TEXT NOT NULL UNIQUE,
            card_type TEXT,
            amount_uzs INTEGER NOT NULL,
            code_amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            paid_at TEXT,
            raw_payload TEXT
        );
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT, body TEXT, type TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, action TEXT, details TEXT, ip TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        INSERT INTO users (id, code_balance) VALUES (1, 0);
        INSERT INTO payment_transactions
            (id, user_id, provider, merchant_trans_id, amount_uzs, code_amount, status)
            VALUES (1, 1, 'click', 'order-1', 10000, 500, 'pending');
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


def _balance(user_id=1):
    return db_module.query_one("SELECT code_balance FROM users WHERE id=?", (user_id,))["code_balance"]


def test_mark_paid_credits_balance_once(ctx):
    ok = payment_gateway.mark_paid("order-1", "click-txn-1")
    assert ok is True
    assert _balance() == 500
    txn = payment_gateway.get_transaction("order-1")
    assert txn["status"] == "paid"


def test_mark_paid_is_idempotent_on_duplicate_webhook(ctx):
    """The exact scenario that was broken: the provider retries the same
    webhook call for a merchant_trans_id already marked paid."""
    ok1 = payment_gateway.mark_paid("order-1", "click-txn-1")
    ok2 = payment_gateway.mark_paid("order-1", "click-txn-1-retry")
    assert ok1 is True
    assert ok2 is True
    assert _balance() == 500  # NOT 1000 — must not double-credit


def test_mark_paid_unknown_transaction_returns_false(ctx):
    ok = payment_gateway.mark_paid("does-not-exist", "txn-x")
    assert ok is False
    assert _balance() == 0
