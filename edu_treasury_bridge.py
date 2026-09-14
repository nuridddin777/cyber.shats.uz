# ============================================================
# EDU <-> EDU G'AZNA (ALOHIDA JAMG'ARMA) BOG'LOVCHISI
# ============================================================
# v33'dan boshlab Edu qismi endi ASOSIY SHATS CYBER G'aznasidan (treasury_fund)
# BUTUNLAY MUSTAQIL, o'zining alohida jamg'armasiga (edu_treasury_fund) ega:
#   - Tashkilot ICHKI xizmatga coin sarflasa (qo'shimcha slot, tarif sotib
#     olish, o'tkazma komissiyasi) -> shu summa edu_treasury_fund'ga tushadi.
#   - Edu admin/G'azna xodimi tashkilotga coin CHIQARSA -> edu_treasury_fund'dan
#     ayiriladi (agar yetarli mablag' bo'lmasa rad etiladi).
#   - Tashkilot tarifni 9 xonali FAOLLASHTIRISH KALITI orqali (coin sarflamasdan)
#     ochishi ham mumkin — bu holda pul harakati bo'lmaydi, faqat kalit
#     "ishlatilgan" deb belgilanadi (audit uchun).
#
# Bu YAGONA fayl orqali Edu qismining barcha moliyaviy oqimi nazorat qilinadi.

import secrets

from db import query_one, query_all, execute
from edu_orgs import EduOrgError, calc_transfer_commission


# ------------------------------------------------------------------
# Ichki: Edu jamg'armasiga kirim/chiqim yozish
# ------------------------------------------------------------------
def _edu_fund_in(amount: int, reason: str, edu_org_id: int = None):
    if amount <= 0:
        return
    execute("UPDATE edu_treasury_fund SET balance = balance + ?, updated_at = datetime('now') WHERE id=1", (amount,))
    execute(
        "INSERT INTO edu_treasury_fund_log (direction, amount, reason, edu_org_id) VALUES ('in', ?, ?, ?)",
        (amount, reason, edu_org_id)
    )


def _edu_fund_out(amount: int, reason: str, edu_org_id: int = None, edu_admin_id: int = None,
                   activation_key_id: int = None) -> bool:
    """MUHIM (tuzatilgan race condition): balans avval ALOHIDA SELECT bilan
    tekshirilib, keyin ALOHIDA UPDATE bilan kamaytirilardi — ikkita deyarli
    bir vaqtdagi chiqarish jamg'armani manfiyga tushirishi mumkin edi. Endi
    tekshirish+kamaytirish BITTA atomik UPDATE...WHERE bilan; agar mablag'
    yetarli bo'lmasa hech narsa o'zgarmaydi va False qaytadi."""
    row = query_one(
        "UPDATE edu_treasury_fund SET balance = balance - ?, updated_at = datetime('now') "
        "WHERE id=1 AND balance >= ? RETURNING balance",
        (amount, amount)
    )
    if not row:
        return False
    execute(
        "INSERT INTO edu_treasury_fund_log (direction, amount, reason, edu_org_id, edu_admin_id, activation_key_id) "
        "VALUES ('out', ?, ?, ?, ?, ?)",
        (amount, reason, edu_org_id, edu_admin_id, activation_key_id)
    )
    return True


def get_edu_fund_balance() -> int:
    """Edu qismining ALOHIDA (asosiy SHATS CYBER'dan mustaqil) jamg'arma balansi."""
    row = query_one("SELECT balance FROM edu_treasury_fund WHERE id=1")
    return row["balance"] if row else 0


# Eski nom bilan ham ishlatilishi mumkin bo'lgan joylar uchun moslik (compat alias).
get_unified_fund_balance = get_edu_fund_balance


# ------------------------------------------------------------------
# Edu tashkiloti coin sarflashi (qo'shimcha slot, tarif sotib olish) -> Edu jamg'armasiga kiradi
# ------------------------------------------------------------------
def charge_org_coins(conn, org_id: int, amount: int, reason: str):
    """
    Tashkilotning coin_balance'idan yechadi va shu summani Edu jamg'armasiga qo'shadi
    (chunki bu — ichki xizmat uchun sarflangan coin).

    MUHIM (tuzatilgan race condition): balans avval ALOHIDA SELECT bilan
    tekshirilib, keyin ALOHIDA UPDATE bilan kamaytirilardi — tashkilot
    nomidan ikkita deyarli bir vaqtdagi xarid (2 marta bosish) bitta
    balansdan ikkalasi ham yechishi mumkin edi. Endi tekshirish+kamaytirish
    BITTA atomik UPDATE...WHERE bilan.
    """
    org = conn.execute("SELECT coin_balance FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if not org:
        raise EduOrgError("Tashkilot topilmadi")

    row = conn.execute(
        "UPDATE edu_organizations SET coin_balance = coin_balance - ? WHERE id=? AND coin_balance >= ? "
        "RETURNING coin_balance",
        (amount, org_id, amount)
    ).fetchone()
    if not row:
        current = conn.execute("SELECT coin_balance FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
        raise EduOrgError(f"Balans yetarli emas: kerak {amount}, mavjud {current['coin_balance']}")

    conn.commit()
    _edu_fund_in(amount, reason, edu_org_id=org_id)


# ------------------------------------------------------------------
# Edu admin tashkilotga coin chiqarishi (Edu jamg'armasidan ayiriladi)
# ------------------------------------------------------------------
def issue_coins_to_org(conn, treasury_account_id: int, org_id: int, amount: int, admin_user_id: int = None,
                        edu_admin_id: int = None):
    """
    Edu jamg'armasidan tashkilotga CODE chiqaradi. Jamg'armada yetarli mablag'
    yo'q bo'lsa rad etadi.

    `edu_admin_id` — AUDIT uchun: amalni bajargan Edu admin (edu_admins.id).
    `admin_user_id`/`treasury_account_id` — orqaga moslik uchun saqlanган,
    hozircha ishlatilmaydi (Edu tomonidan chiqarilgan coinlar endi faqat
    Edu admin orqali chiqariladi).
    """
    if amount <= 0:
        raise EduOrgError("Miqdor musbat bo'lishi kerak")

    org = conn.execute("SELECT id FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if not org:
        raise EduOrgError("Tashkilot topilmadi")

    if not _edu_fund_out(amount, "issue_to_edu_org", edu_org_id=org_id, edu_admin_id=edu_admin_id):
        balance = get_edu_fund_balance()
        raise EduOrgError(f"Edu jamg'armasida yetarli mablag' yo'q. Kerak: {amount}, jamg'armada: {balance}")

    conn.execute("UPDATE edu_organizations SET coin_balance = coin_balance + ? WHERE id=?", (amount, org_id))
    conn.commit()


# ------------------------------------------------------------------
# 9 xonali faollashtirish kaliti — Edu admin chiqaradi, tashkilot ishlatadi
# ------------------------------------------------------------------
def generate_activation_key(conn, tarif_code: str, months: int, edu_admin_id: int = None) -> str:
    """Edu admin tomonidan chiqariladigan, bir martalik, 9 xonali raqamli
    faollashtirish kaliti yaratadi (coin sarflamasdan tarif ochish uchun)."""
    tarif = conn.execute("SELECT code FROM edu_tariffs WHERE code=?", (tarif_code,)).fetchone()
    if not tarif:
        raise EduOrgError("Bunday tarif topilmadi")
    if months < 1:
        months = 1

    for _ in range(20):
        key_code = "".join(secrets.choice("0123456789") for _ in range(9))
        exists = conn.execute("SELECT 1 FROM edu_activation_keys WHERE key_code=?", (key_code,)).fetchone()
        if not exists:
            break
    else:
        raise EduOrgError("Kalit generatsiya qilib bo'lmadi, qayta urinib ko'ring")

    conn.execute(
        "INSERT INTO edu_activation_keys (key_code, tarif_code, months, created_by_edu_admin_id) "
        "VALUES (?,?,?,?)",
        (key_code, tarif_code, months, edu_admin_id)
    )
    conn.commit()
    return key_code


def mark_activation_key_used(conn, key_id: int, org_id: int):
    conn.execute(
        "UPDATE edu_activation_keys SET is_used=1, used_by_org_id=?, used_at=datetime('now') WHERE id=?",
        (org_id, key_id)
    )


# ------------------------------------------------------------------
# Markazning haqiqiy pul evaziga CODE sotib olish so'rovi (karta + chek)
# ------------------------------------------------------------------
def create_org_purchase_request(org_id: int, amount: int, price_uzs: int, receipt_file_path: str):
    if amount <= 0:
        raise EduOrgError("Miqdor musbat bo'lishi kerak.")
    if not receipt_file_path:
        raise EduOrgError("To'lov cheki (rasm) majburiy.")
    execute(
        "INSERT INTO edu_purchase_requests (org_id, code_amount, price_uzs, receipt_file_path) "
        "VALUES (?,?,?,?)",
        (org_id, amount, price_uzs, receipt_file_path)
    )


def get_org_purchase_requests(org_id: int, limit: int = 20):
    return query_all(
        "SELECT * FROM edu_purchase_requests WHERE org_id=? ORDER BY id DESC LIMIT ?",
        (org_id, limit)
    )


def get_purchase_requests(status: str = "pending", limit: int = 200):
    if status == "all":
        return query_all(
            """SELECT r.*, o.name as org_name, o.org_number FROM edu_purchase_requests r
               JOIN edu_organizations o ON o.id = r.org_id ORDER BY r.id DESC LIMIT ?""",
            (limit,)
        )
    return query_all(
        """SELECT r.*, o.name as org_name, o.org_number FROM edu_purchase_requests r
           JOIN edu_organizations o ON o.id = r.org_id WHERE r.status=? ORDER BY r.id DESC LIMIT ?""",
        (status, limit)
    )


def approve_purchase_request(conn, request_id: int, treasury_account_id: int = None):
    req = conn.execute("SELECT * FROM edu_purchase_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        raise EduOrgError("So'rov topilmadi.")
    if req["status"] != "pending":
        raise EduOrgError(f"Bu so'rov allaqachon ko'rib chiqilgan ({req['status']}).")

    # Edu jamg'armasidan chiqarish (asosiy saytdagi issue_coins_to_user bilan
    # AYNAN bir xil mantiq — jamg'armada yetarli mablag' bo'lishi shart).
    issue_coins_to_org(conn, treasury_account_id, req["org_id"], req["code_amount"])

    conn.execute(
        "UPDATE edu_purchase_requests SET status='completed', reviewed_by=?, "
        "reviewed_at=datetime('now') WHERE id=?",
        (treasury_account_id, request_id)
    )
    conn.commit()
    return req


def reject_purchase_request(conn, request_id: int, treasury_account_id: int = None, reason: str = ""):
    req = conn.execute("SELECT * FROM edu_purchase_requests WHERE id=?", (request_id,)).fetchone()
    if not req:
        raise EduOrgError("So'rov topilmadi.")
    if req["status"] != "pending":
        raise EduOrgError(f"Bu so'rov allaqachon ko'rib chiqilgan ({req['status']}).")

    conn.execute(
        "UPDATE edu_purchase_requests SET status='rejected', reviewed_by=?, "
        "reviewed_at=datetime('now'), admin_note=? WHERE id=?",
        (treasury_account_id, reason, request_id)
    )
    conn.commit()
    return req


def deposit_to_edu_fund(amount: int, note: str = "", treasury_account_id: int = None):
    """G'azna xodimi Edu jamg'armasiga to'g'ridan-to'g'ri CODE qo'shadi
    (masalan real pul kiritilganda, jamg'armani "to'ldirish" uchun) —
    asosiy saytdagi admin_deposit_to_fund bilan bir xil mantiq."""
    if amount <= 0:
        raise EduOrgError("Miqdor musbat bo'lishi kerak.")
    _edu_fund_in(amount, f"treasury_deposit:{note}" if note else "treasury_deposit",
                 edu_org_id=None)


# ------------------------------------------------------------------
# O'qituvchi/o'quvchi o'rtasida (yoki tashkilot ichida) coin o'tkazmasi
# ------------------------------------------------------------------
def execute_coin_transfer(conn, org_id: int, sender_type: str, sender_id: int,
                           receiver_type: str, receiver_id: int, amount: int,
                           is_free_gift: bool = False):
    """
    Komissiya bilan coin o'tkazmasi. `sender_type`/`receiver_type` — 'teacher' | 'student'.
    is_free_gift=True bo'lsa — 1 martalik "5 tanga bepul jo'natish" ishlatiladi
    (komissiyasiz, lekin faqat aniq 5 tanga uchun).
    Komissiya Edu jamg'armasiga qo'shiladi.
    """
    table = {"teacher": "edu_teachers", "student": "edu_students"}
    if sender_type not in table or receiver_type not in table:
        raise EduOrgError("Noto'g'ri foydalanuvchi turi")

    sender = conn.execute(f"SELECT coin_balance FROM {table[sender_type]} WHERE id=? AND org_id=?",
                           (sender_id, org_id)).fetchone()
    receiver = conn.execute(f"SELECT id FROM {table[receiver_type]} WHERE id=? AND org_id=?",
                             (receiver_id, org_id)).fetchone()
    if not sender or not receiver:
        raise EduOrgError("Yuboruvchi yoki qabul qiluvchi topilmadi (bir tashkilot ichida bo'lishi shart)")

    if is_free_gift:
        from edu_orgs import can_send_free_gift, consume_free_gift
        if amount != 5:
            raise EduOrgError("Bepul sovg'a faqat aniq 5 tanga uchun ishlatiladi")
        if not can_send_free_gift(conn, sender_type, sender_id):
            raise EduOrgError("5 tanga bepul jo'natish huquqi qolmagan")
        commission = 0
    else:
        commission = calc_transfer_commission(conn, amount)

    total_needed = amount + commission
    # MUHIM (tuzatilgan race condition): avval balans ALOHIDA SELECT bilan
    # tekshirilib, keyin ALOHIDA UPDATE bilan kamaytirilardi — bitta atomik
    # UPDATE...WHERE bilan almashtirildi (coins.spend_coins()dagi kabi).
    row = conn.execute(
        f"UPDATE {table[sender_type]} SET coin_balance = coin_balance - ? WHERE id=? AND coin_balance >= ? "
        f"RETURNING coin_balance",
        (total_needed, sender_id, total_needed)
    ).fetchone()
    if not row:
        raise EduOrgError(f"Balans yetarli emas: kerak {total_needed} (o'tkazma {amount} + komissiya {commission})")

    conn.execute(f"UPDATE {table[receiver_type]} SET coin_balance = coin_balance + ? WHERE id=?",
                 (amount, receiver_id))
    conn.commit()

    if is_free_gift:
        consume_free_gift(conn, sender_type, sender_id)
    elif commission:
        _edu_fund_in(commission, "edu_transfer_fee", edu_org_id=org_id)

    return {"amount": amount, "commission": commission, "total_charged": total_needed}
