"""
Unit tests for edu_treasury_bridge.py's coin-moving functions — same TOCTOU
race class fixed elsewhere (coins.spend_coins, chests.py, treasury.py,
payment_gateway.py): each of these checked a balance via a separate SELECT
in Python, then decremented it via a separate UPDATE. Fixed with the atomic
UPDATE ... WHERE balance >= amount ... RETURNING pattern.
"""
import sqlite3

import pytest

import db as db_module
import edu_treasury_bridge as bridge


@pytest.fixture()
def app(tmp_path, monkeypatch):
    import app as flask_app_module

    test_db_path = str(tmp_path / "test_edu_treasury.db")
    conn = sqlite3.connect(test_db_path)
    conn.executescript(
        """
        CREATE TABLE edu_organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, coin_balance INTEGER DEFAULT 0
        );
        CREATE TABLE edu_teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, org_id INTEGER NOT NULL, coin_balance INTEGER DEFAULT 0
        );
        CREATE TABLE edu_students (
            id INTEGER PRIMARY KEY AUTOINCREMENT, org_id INTEGER NOT NULL, coin_balance INTEGER DEFAULT 0
        );
        CREATE TABLE edu_treasury_fund (
            id INTEGER PRIMARY KEY CHECK (id=1), balance INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE edu_treasury_fund_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, direction TEXT NOT NULL, amount INTEGER NOT NULL,
            reason TEXT NOT NULL, edu_org_id INTEGER, edu_admin_id INTEGER, activation_key_id INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE edu_coin_commission (
            id INTEGER PRIMARY KEY AUTOINCREMENT, min_amount INTEGER NOT NULL,
            max_amount INTEGER NOT NULL, commission_coins INTEGER NOT NULL
        );
        INSERT INTO edu_organizations (id, coin_balance) VALUES (1, 500);
        INSERT INTO edu_teachers (id, org_id, coin_balance) VALUES (1, 1, 50);
        INSERT INTO edu_students (id, org_id, coin_balance) VALUES (1, 1, 0);
        INSERT INTO edu_treasury_fund (id, balance) VALUES (1, 1000);
        INSERT INTO edu_coin_commission (min_amount, max_amount, commission_coins) VALUES (0, 9999, 0);
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


def test_charge_org_coins_success(ctx):
    conn = db_module.get_db()
    bridge.charge_org_coins(conn, 1, 200, "edu_extra_teacher")
    org = db_module.query_one("SELECT coin_balance FROM edu_organizations WHERE id=1")
    assert org["coin_balance"] == 300
    assert bridge.get_edu_fund_balance() == 1200  # 1000 + 200 (moved into the edu fund)


def test_charge_org_coins_insufficient_balance_raises_and_leaves_state(ctx):
    conn = db_module.get_db()
    with pytest.raises(bridge.EduOrgError):
        bridge.charge_org_coins(conn, 1, 9999, "edu_extra_teacher")
    org = db_module.query_one("SELECT coin_balance FROM edu_organizations WHERE id=1")
    assert org["coin_balance"] == 500  # unchanged
    assert bridge.get_edu_fund_balance() == 1000  # unchanged


def test_issue_coins_to_org_success(ctx):
    conn = db_module.get_db()
    bridge.issue_coins_to_org(conn, None, 1, 300)
    org = db_module.query_one("SELECT coin_balance FROM edu_organizations WHERE id=1")
    assert org["coin_balance"] == 800
    assert bridge.get_edu_fund_balance() == 700


def test_issue_coins_to_org_insufficient_fund_raises_and_leaves_state(ctx):
    conn = db_module.get_db()
    with pytest.raises(bridge.EduOrgError):
        bridge.issue_coins_to_org(conn, None, 1, 99999)
    org = db_module.query_one("SELECT coin_balance FROM edu_organizations WHERE id=1")
    assert org["coin_balance"] == 500  # unchanged
    assert bridge.get_edu_fund_balance() == 1000  # unchanged


def test_execute_coin_transfer_success(ctx):
    conn = db_module.get_db()
    result = bridge.execute_coin_transfer(conn, 1, "teacher", 1, "student", 1, 20)
    assert result["total_charged"] == 20
    teacher = db_module.query_one("SELECT coin_balance FROM edu_teachers WHERE id=1")
    student = db_module.query_one("SELECT coin_balance FROM edu_students WHERE id=1")
    assert teacher["coin_balance"] == 30
    assert student["coin_balance"] == 20


def test_execute_coin_transfer_insufficient_balance_leaves_state(ctx):
    conn = db_module.get_db()
    with pytest.raises(bridge.EduOrgError):
        bridge.execute_coin_transfer(conn, 1, "teacher", 1, "student", 1, 999)
    teacher = db_module.query_one("SELECT coin_balance FROM edu_teachers WHERE id=1")
    student = db_module.query_one("SELECT coin_balance FROM edu_students WHERE id=1")
    assert teacher["coin_balance"] == 50  # unchanged
    assert student["coin_balance"] == 0  # unchanged
