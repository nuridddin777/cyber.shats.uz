"""
CYBER SHATS — Jamoa (Team) va Jamoa Jamg'armasi moduli.

Har bir foydalanuvchi (tarifidan qat'iy nazar) jamoa ochishi mumkin, lekin
buning uchun oylik "soliq" to'lanadi:
  - FREE foydalanuvchi:            team_tax_free_code   (masalan 3 CODE/oy)
  - Pro / Cyber Pro / VIP:         team_tax_paid_code    (masalan 2 CODE/oy)
  - MAXSUS (hacker):               dastlabki N oy bepul, keyin team_tax_hacker_code

Jamoa yaratilganda avtomatik ketma-ket 5 xonali ID beriladi (masalan '00001').
Jamg'arma orqali a'zolar CODE yig'adi, undan a'zoga Pro/versiya xarid qilib
berish yoki sovg'a qilish mumkin.
"""
from datetime import datetime, timedelta
from db import query_one, query_all, execute
from coins import get_balance, add_coins, spend_coins
from pricing import get_price


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------

def _now():
    return datetime.now()


def _fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _next_custom_id():
    """Ketma-ket 5 xonali jamoa ID (00001, 00002, ...)."""
    row = query_one("SELECT custom_id FROM teams ORDER BY id DESC LIMIT 1")
    if not row or not row.get("custom_id"):
        return "00001"
    try:
        n = int(row["custom_id"]) + 1
    except ValueError:
        n = 1
    return f"{n:05d}"


def get_team_tax(plan: str) -> int:
    """Tariflar olib tashlangan — jamoa solig'i endi har doim bepul (0)."""
    return 0


# ---------------------------------------------------------------------------
# Jamoa CRUD
# ---------------------------------------------------------------------------

def get_user_team(user_id: int):
    """Foydalanuvchi a'zo bo'lgan jamoani qaytaradi (agar bor bo'lsa)."""
    row = query_one(
        """SELECT t.*, tm.role FROM teams t
           JOIN team_members tm ON tm.team_id = t.id
           WHERE tm.user_id = ?""",
        (user_id,)
    )
    return row


def create_team(user_id: int, name: str, description: str = "") -> tuple[bool, str, dict | None]:
    """Yangi jamoa yaratadi. Foydalanuvchi allaqachon jamoada bo'lsa rad etadi.
    Tarifiga qarab oylik soliq (yoki MAXSUS uchun bepul davr) hisoblanadi."""
    if get_user_team(user_id):
        return False, "Siz allaqachon bir jamoaga a'zosiz. Avval undan chiqing.", None

    name = (name or "").strip()
    if not name or len(name) < 2:
        return False, "Jamoa nomini kiriting (kamida 2 belgi).", None

    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    plan = user.get("plan") if user else "free"

    tax_free_until = None
    next_billing_at = None

    if plan == "hacker":
        free_months = get_price("team_hacker_free_months")
        tax_free_until = _fmt(_now() + timedelta(days=30 * free_months))
        next_billing_at = tax_free_until
    else:
        tax = get_team_tax(plan)
        if tax > 0:
            balance = get_balance(user_id)
            if balance < tax:
                return False, f"Jamoa ochish uchun {tax} CODE soliq kerak. Yetishmayapti: {tax - balance} CODE.", None
            ok, msg = spend_coins(user_id, tax, "team_tax")
            if not ok:
                return False, msg, None
        next_billing_at = _fmt(_now() + timedelta(days=30))

    custom_id = _next_custom_id()
    execute(
        """INSERT INTO teams (custom_id, name, leader_id, description, status, next_billing_at, tax_free_until)
           VALUES (?,?,?,?, 'active', ?, ?)""",
        (custom_id, name, user_id, description, next_billing_at, tax_free_until)
    )
    team = query_one("SELECT * FROM teams WHERE custom_id=?", (custom_id,))
    execute("INSERT INTO team_members (team_id, user_id, role) VALUES (?,?,'leader')", (team["id"], user_id))
    execute("INSERT INTO team_treasury (team_id, balance) VALUES (?, 0)", (team["id"],))
    return True, f"Jamoa yaratildi! ID: #{custom_id}", team


def leave_team(user_id: int) -> tuple[bool, str]:
    team = get_user_team(user_id)
    if not team:
        return False, "Siz hech qanday jamoada emassiz."
    if team["role"] == "leader":
        member_count = query_one("SELECT COUNT(*) c FROM team_members WHERE team_id=?", (team["id"],))["c"]
        if member_count > 1:
            return False, "Lider sifatida chiqishdan oldin liderlikni boshqa a'zoga o'tkazing yoki jamoani tarqating."
        # Yagona a'zo bo'lsa — jamoani butunlay tarqatadi
        return dissolve_team(user_id)
    execute("DELETE FROM team_members WHERE team_id=? AND user_id=?", (team["id"], user_id))
    return True, "Jamoadan chiqdingiz."


def dissolve_team(leader_id: int) -> tuple[bool, str]:
    team = get_user_team(leader_id)
    if not team or team["role"] != "leader":
        return False, "Faqat lider jamoani tarqatishi mumkin."
    # Jamg'armadagi qolgan CODE'ni a'zolarga mutanosib qaytarish
    treasury = query_one("SELECT * FROM team_treasury WHERE team_id=?", (team["id"],))
    if treasury and treasury["balance"] > 0:
        members = query_all("SELECT * FROM team_members WHERE team_id=?", (team["id"],))
        contributions = query_all(
            "SELECT user_id, SUM(amount) as total FROM team_treasury_log WHERE team_id=? AND direction='in' GROUP BY user_id",
            (team["id"],)
        )
        total_contributed = sum(r["total"] for r in contributions) or 1
        remaining = treasury["balance"]
        for c in contributions:
            share = int(treasury["balance"] * (c["total"] / total_contributed))
            share = min(share, remaining)
            if share > 0:
                add_coins(c["user_id"], share, "team_refund", team["id"])
                remaining -= share
    execute("DELETE FROM team_treasury_log WHERE team_id=?", (team["id"],))
    execute("DELETE FROM team_treasury WHERE team_id=?", (team["id"],))
    execute("DELETE FROM team_invites WHERE team_id=?", (team["id"],))
    execute("DELETE FROM team_members WHERE team_id=?", (team["id"],))
    execute("DELETE FROM teams WHERE id=?", (team["id"],))
    return True, "Jamoa tarqatildi, jamg'armadagi CODE a'zolarga hissasiga qarab qaytarildi."


# ---------------------------------------------------------------------------
# Taklif (invite)
# ---------------------------------------------------------------------------

def create_invite(team_id: int, created_by: int) -> str:
    import uuid
    code = uuid.uuid4().hex[:8].upper()
    execute("INSERT INTO team_invites (team_id, invite_code, created_by) VALUES (?,?,?)",
            (team_id, code, created_by))
    return code


def join_via_invite(user_id: int, invite_code: str) -> tuple[bool, str]:
    if get_user_team(user_id):
        return False, "Siz allaqachon bir jamoaga a'zosiz."
    invite = query_one("SELECT * FROM team_invites WHERE invite_code=?", (invite_code.strip().upper(),))
    if not invite:
        return False, "Taklif kodi topilmadi yoki eskirgan."
    execute("INSERT INTO team_members (team_id, user_id, role) VALUES (?,?,'member')", (invite["team_id"], user_id))
    team = query_one("SELECT * FROM teams WHERE id=?", (invite["team_id"],))
    return True, f"'{team['name']}' jamoasiga muvaffaqiyatli qo'shildingiz!"


# ---------------------------------------------------------------------------
# Jamg'arma (Treasury)
# ---------------------------------------------------------------------------

def contribute(user_id: int, amount: int) -> tuple[bool, str]:
    team = get_user_team(user_id)
    if not team:
        return False, "Avval jamoaga a'zo bo'ling."
    if amount <= 0:
        return False, "Miqdorni to'g'ri kiriting."
    ok, msg = spend_coins(user_id, amount, "team_contribute", team["id"])
    if not ok:
        return False, msg
    execute("UPDATE team_treasury SET balance = balance + ?, updated_at=datetime('now') WHERE team_id=?",
            (amount, team["id"]))
    execute("INSERT INTO team_treasury_log (team_id, user_id, direction, amount, reason) VALUES (?,?,?,?,?)",
            (team["id"], user_id, "in", amount, "contribute"))
    return True, f"{amount:,} CODE jamg'armaga qo'shildi!"


def get_treasury(team_id: int):
    return query_one("SELECT * FROM team_treasury WHERE team_id=?", (team_id,))


def get_treasury_log(team_id: int, limit: int = 30):
    return query_all(
        """SELECT l.*, u.ism, u.familiya FROM team_treasury_log l
           LEFT JOIN users u ON u.id = l.user_id
           WHERE l.team_id=? ORDER BY l.id DESC LIMIT ?""",
        (team_id, limit)
    )


def gift_plan_from_treasury(leader_id: int, target_user_id: int, plan_key: str) -> tuple[bool, str]:
    """Jamg'armadagi CODE bilan a'zoga plan (pro/cyber_pro/vip) sotib olib sovg'a qiladi.
    Faqat lider (yoki moderator) amalga oshira oladi."""
    team = get_user_team(leader_id)
    if not team or team["role"] not in ("leader", "moderator"):
        return False, "Faqat jamoa lideri yoki moderatori sovg'a bera oladi."
    target_member = query_one("SELECT * FROM team_members WHERE team_id=? AND user_id=?", (team["id"], target_user_id))
    if not target_member:
        return False, "Bu foydalanuvchi jamoa a'zosi emas."

    price_key = {"pro": "pro_price_code", "cyber_pro": "cyber_pro_price_code", "vip": "vip_price_code"}.get(plan_key)
    if not price_key:
        return False, "Noto'g'ri versiya tanlandi."
    cost = get_price(price_key)

    # MUHIM (tuzatilgan race condition): jamg'arma balansi avval ALOHIDA
    # SELECT bilan tekshirilib, keyin ALOHIDA UPDATE bilan kamaytirilardi —
    # jamoaning bir nechta lider/moderatori deyarli bir vaqtda sovg'a bersa,
    # ikkalasi ham HALI kamaytirilmagan balansni o'qib, ikkalasi ham
    # o'tkazishi mumkin edi. Endi BITTA atomik UPDATE...WHERE bilan.
    updated = query_one(
        "UPDATE team_treasury SET balance = balance - ?, updated_at=datetime('now') "
        "WHERE team_id=? AND balance >= ? RETURNING balance",
        (cost, team["id"], cost)
    )
    if not updated:
        treasury = get_treasury(team["id"])
        need = cost - (treasury["balance"] if treasury else 0)
        return False, f"Jamg'armada yetarli CODE yo'q. Kerak: {cost}, yetishmayapti: {need}."

    execute("INSERT INTO team_treasury_log (team_id, user_id, direction, amount, reason, note) VALUES (?,?,?,?,?,?)",
            (team["id"], target_user_id, "out", cost, "gift_plan", plan_key))

    expires_at = _fmt(_now() + timedelta(days=30))
    execute("UPDATE users SET plan=?, plan_expires_at=? WHERE id=?", (plan_key, expires_at, target_user_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (target_user_id, "Jamoa sovg'asi!",
             f"Jamoangiz jamg'armasidan sizga {plan_key.upper()} versiyasi sovg'a qilindi!", "success"))
    return True, f"{plan_key.upper()} versiyasi a'zoga muvaffaqiyatli sovg'a qilindi!"


# ---------------------------------------------------------------------------
# Oylik soliq (billing)
# ---------------------------------------------------------------------------

def check_and_charge_tax(team: dict) -> dict:
    """Jamoa sahifasiga kirishda chaqiriladi: muddati o'tgan bo'lsa, liderdan
    avtomatik soliqni yechishga urinadi. Natija holatini qaytaradi."""
    if not team.get("next_billing_at"):
        return {"charged": False, "frozen": False}

    now = _now()
    try:
        due = datetime.strptime(team["next_billing_at"], "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return {"charged": False, "frozen": False}

    if now < due:
        return {"charged": False, "frozen": False}

    leader = query_one("SELECT * FROM users WHERE id=?", (team["leader_id"],))
    plan = leader.get("plan") if leader else "free"
    tax = get_price("team_tax_hacker_code") if plan == "hacker" else get_team_tax(plan)

    ok, _ = spend_coins(team["leader_id"], tax, "team_tax", team["id"])
    if ok:
        new_due = _fmt(now + timedelta(days=30))
        execute("UPDATE teams SET next_billing_at=?, status='active' WHERE id=?", (new_due, team["id"]))
        return {"charged": True, "frozen": False, "amount": tax}
    else:
        execute("UPDATE teams SET status='frozen' WHERE id=?", (team["id"],))
        return {"charged": False, "frozen": True, "amount": tax}


def pay_pending_tax(user_id: int) -> tuple[bool, str]:
    team = get_user_team(user_id)
    if not team or team["role"] != "leader":
        return False, "Faqat lider to'lay oladi."
    leader = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    plan = leader.get("plan") if leader else "free"
    tax = get_price("team_tax_hacker_code") if plan == "hacker" else get_team_tax(plan)
    ok, msg = spend_coins(user_id, tax, "team_tax", team["id"])
    if not ok:
        return False, msg
    new_due = _fmt(_now() + timedelta(days=30))
    execute("UPDATE teams SET next_billing_at=?, status='active' WHERE id=?", (new_due, team["id"]))
    return True, f"Soliq to'landi ({tax} CODE). Jamoa faollashtirildi."
