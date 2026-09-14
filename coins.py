"""
CYBER SHATS — Code tangalari (coin) moduli
Barcha tangalar bilan bog'liq amallar shu yerda.

Foydalanuvchi sarflagan har bir coin (Pro sotib olish, kurs sotib olish,
AI ishlatish) va har bir P2P o'tkazma komissiyasi G'AZNA JAMG'ARMASIGA tushadi
(treasury_fund). G'azna shu jamg'armadan foydalanuvchilarga coin chiqaradi —
agar jamg'armada yetarli mablag' bo'lmasa, chiqarib bera olmaydi.
"""
from db import query_one, execute, log_action, get_db
from config import Config
from pricing import get_price


def get_balance(user_id: int) -> int:
    row = query_one("SELECT code_balance FROM users WHERE id=?", (user_id,))
    return (row["code_balance"] or 0) if row else 0


def add_coins(user_id: int, amount: int, reason: str, ref_id=None):
    """Foydalanuvchiga code tangasi qo'shadi (G'aznadan mustaqil — masalan kurs mukofoti, bonus)."""
    execute("UPDATE users SET code_balance = code_balance + ? WHERE id=?", (amount, user_id))
    execute("INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, amount, reason, ref_id))


def spend_coins(user_id: int, amount: int, reason: str, ref_id=None) -> tuple[bool, str]:
    """Tangalarni sarflaydi. Returns: (success, message)

    MUHIM (tuzatilgan race condition): avval balans ALOHIDA SELECT bilan
    o'qilib, keyin ALOHIDA UPDATE bilan kamaytirilardi. Agar bitta
    foydalanuvchi ikkita so'rovni deyarli bir vaqtda yuborsa (masalan
    "Sotib olish" tugmasini ikki marta bossa, yoki ikkita brauzer
    tabida) — ikkalasi ham HALI KAMAYTIRILMAGAN balansni o'qib, ikkalasi
    ham "yetarli" deb xulosa qilib, ikkalasi ham kamaytirishi mumkin edi —
    natijada balans manfiyga tushib qolardi. Endi bitta atomik
    UPDATE...WHERE bilan: balans faqat "hozir ham yetarli bo'lsa"
    kamaytiriladi, va bu tekshiruv bilan kamaytirish BITTA, bo'linmas
    operatsiya (Postgres bu qatorni operatsiya davomida qulflaydi)."""
    if amount <= 0:
        return False, "Miqdor musbat bo'lishi kerak."
    row = query_one(
        "UPDATE users SET code_balance = code_balance - ? WHERE id = ? AND code_balance >= ? RETURNING code_balance",
        (amount, user_id, amount)
    )
    if not row:
        balance = get_balance(user_id)
        return False, f"Yetarli code tangasi yo'q. Kerak: {amount:,}, mavjud: {balance:,}"
    execute("INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, -amount, reason, ref_id))
    return True, "OK"


def refund_coins(user_id: int, amount: int, reason: str, ref_id=None):
    """MUHIM: pul yechilgandan KEYIN mahsulot berish (ID o'zgartirish,
    ramka/galichka berish va h.k.) biror sababdan MUVAFFAQIYATSIZ bo'lsa
    — foydalanuvchi PULINI YO'QOTMASLIGI uchun shu funksiya orqali
    AVTOMATIK qaytariladi. Har bir xarid funksiyasida spend_coins()dan
    keyingi qadamlar try/except bilan o'ralgan, xato bo'lsa shu
    chaqiriladi."""
    if amount <= 0:
        return
    execute("UPDATE users SET code_balance = code_balance + ? WHERE id=?", (amount, user_id))
    execute("INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, amount, f"refund_{reason}", ref_id))


def _treasury_fund_in(amount: int, reason: str, user_id: int = None):
    """Jamg'armaga kirim qo'shadi (foydalanuvchi sarfi yoki komissiya)."""
    if amount <= 0:
        return
    execute("UPDATE treasury_fund SET balance = balance + ?, updated_at = datetime('now') WHERE id=1", (amount,))
    execute(
        "INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('in', ?, ?, ?)",
        (amount, reason, user_id)
    )


def award_course_completion(user_id: int, course_id: int):
    """Kurs bitirilganda mukofot beradi (bir marta).
    Oddiy foydalanuvchi: 100 code (course_reward_code)
    Cyber Pro foydalanuvchi: + qo'shimcha 1000 code (cyber_pro_course_bonus)
    VIP foydalanuvchi: + qo'shimcha 2000 code (vip_course_bonus)"""
    existing = query_one(
        "SELECT id FROM code_transactions WHERE user_id=? AND reason='course_complete' AND ref_id=?",
        (user_id, course_id)
    )
    if existing:
        return  # Allaqachon berilgan
    add_coins(user_id, get_price("course_reward_code"), "course_complete", course_id)
    # Cyber Pro / VIP qo'shimcha bonus
    user = query_one("SELECT plan FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") == "cyber_pro":
        bonus = get_price("cyber_pro_course_bonus")
        if bonus > 0:
            add_coins(user_id, bonus, "cyber_pro_course_bonus", course_id)
    elif user and user.get("plan") == "vip":
        bonus = get_price("vip_course_bonus")
        if bonus > 0:
            add_coins(user_id, bonus, "vip_course_bonus", course_id)
    # Reyting yangilash
    _update_rating(user_id)
    # Do'stlar faoliyat lentasi uchun
    try:
        import friends as _friends
        course = query_one("SELECT title FROM courses WHERE id=?", (course_id,))
        _friends.log_activity(user_id, "course_done", course["title"] if course else "")
    except Exception:
        pass


def buy_pro_with_coins(user_id: int, override_cost: int = None) -> tuple[bool, str]:
    """Pro versiya sotib olish (narx bazadan, admin tomonidan o'zgartiriladi).
    Sarflangan coin G'azna jamg'armasiga tushadi. 1 oy amal qiladi.

    override_cost: agar berilsa (masalan bot orqali arzonroq narxda sotib
    olish uchun), standart narx o'rniga shu narx ishlatiladi."""
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") in ("pro", "cyber_pro", "vip"):
        return False, "Siz allaqachon Pro yoki yuqori versiya foydalanuvchisiz."
    cost = override_cost if override_cost is not None else get_price("pro_price_code")
    ok, msg = spend_coins(user_id, cost, "buy_pro")
    if not ok:
        return False, msg
    expires_at = _calc_plan_expiry()
    execute("UPDATE users SET plan='pro', plan_expires_at=? WHERE id=?", (expires_at, user_id))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", cost, "success"))
    log_action(user_id, "buy_pro_code", details=f"cost:{cost},expires:{expires_at}")
    _treasury_fund_in(cost, "buy_pro", user_id)
    return True, f"Pro versiya faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha). Tabriklaymiz!"


def buy_cyber_pro_with_coins(user_id: int, override_cost: int = None) -> tuple[bool, str]:
    """Cyber Pro versiyasi — Pro'dan kuchliroq. Ingliz tili, matematika, Office yo'nalishlari ochiladi.
    Komissiyasiz P2P, 10,000 welcome bonus, har kurs bitirishda 1,000 code bonus. 1 oy amal qiladi."""
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") in ("cyber_pro", "vip"):
        return False, "Siz allaqachon Cyber Pro yoki yuqori versiya foydalanuvchisiz."
    cost = override_cost if override_cost is not None else get_price("cyber_pro_price_code")
    ok, msg = spend_coins(user_id, cost, "buy_cyber_pro")
    if not ok:
        return False, msg
    expires_at = _calc_plan_expiry()
    execute("UPDATE users SET plan='cyber_pro', plan_expires_at=? WHERE id=?", (expires_at, user_id))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", cost, "success"))
    log_action(user_id, "buy_cyber_pro_code", details=f"cost:{cost},expires:{expires_at}")
    _treasury_fund_in(cost, "buy_cyber_pro", user_id)
    # Avtomatik bonus olib tashlandi — endi bonuslarni faqat admin panel orqali beriladi.
    return True, f"Cyber Pro faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha)."


def buy_vip_with_coins(user_id: int, override_cost: int = None) -> tuple[bool, str]:
    """SHATS CYBER PRO — eng kuchli versiya. Pro va Cyber Pro'dagi hamma narsa + ko'proq bonus.
    Tilla-rang dizayn. 1 oy amal qiladi. Admin yoqib/o'chirib qo'yishi mumkin."""
    if get_price("vip_enabled") != 1 and get_price("vip_enabled") != "1":
        return False, "SHATS CYBER PRO versiya hozircha vaqtincha o'chirilgan."
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") == "vip":
        return False, "Siz allaqachon SHATS CYBER PRO foydalanuvchisiz."
    cost = override_cost if override_cost is not None else get_price("vip_price_code")
    ok, msg = spend_coins(user_id, cost, "buy_vip")
    if not ok:
        return False, msg
    expires_at = _calc_plan_expiry()
    execute("UPDATE users SET plan='vip', plan_expires_at=? WHERE id=?", (expires_at, user_id))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", cost, "success"))
    log_action(user_id, "buy_vip_code", details=f"cost:{cost},expires:{expires_at}")
    _treasury_fund_in(cost, "buy_vip", user_id)
    # Avtomatik bonus olib tashlandi — endi bonuslarni faqat admin panel orqali beriladi.
    return True, f"🔥 SHATS CYBER PRO faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha)."


def buy_hacker_with_coins(user_id: int, override_cost: int = None) -> tuple[bool, str]:
    """MAXSUS versiya — binafsha-haker uslubidagi eksklyuziv tarif. 1 oy amal qiladi."""
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user and user.get("plan") == "hacker":
        return False, "Siz allaqachon MAXSUS versiya foydalanuvchisiz."
    cost = override_cost if override_cost is not None else get_price("hacker_price_code")
    ok, msg = spend_coins(user_id, cost, "buy_hacker")
    if not ok:
        return False, msg
    expires_at = _calc_plan_expiry()
    execute("UPDATE users SET plan='hacker', plan_expires_at=? WHERE id=?", (expires_at, user_id))
    execute("INSERT INTO pro_payments (user_id, method, amount_code, status) VALUES (?,?,?,?)",
            (user_id, "code", cost, "success"))
    log_action(user_id, "buy_hacker_code", details=f"cost:{cost},expires:{expires_at}")
    _treasury_fund_in(cost, "buy_hacker", user_id)
    return True, f"⚡ MAXSUS versiya faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha)."


def _calc_plan_expiry() -> str:
    """Joriy vaqtdan plan_duration_days kun keyingi sana (ISO format)."""
    import datetime
    days = get_price("plan_duration_days")
    try:
        days = int(days)
    except (ValueError, TypeError):
        days = 30
    return (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()


def check_and_downgrade_expired_plan(user_id: int) -> bool:
    """
    Foydalanuvchining Pro/Cyber Pro/VIP muddati tugaganmi tekshiradi.
    Tugagan bo'lsa avtomatik 'free'ga tushiradi. True qaytaradi agar tushirilgan bo'lsa.
    Bu funksiya har bir muhim sahifa ochilganda chaqiriladi (fon jarayoni shart emas).
    """
    import datetime
    user = query_one("SELECT plan, plan_expires_at FROM users WHERE id=?", (user_id,))
    if not user or user["plan"] not in ("pro", "cyber_pro", "vip"):
        return False
    if not user["plan_expires_at"]:
        return False
    try:
        expires = datetime.datetime.fromisoformat(user["plan_expires_at"])
    except ValueError:
        return False
    if datetime.datetime.now() < expires:
        return False

    # Muddati tugagan — free'ga tushiramiz
    old_plan = user["plan"]
    execute("UPDATE users SET plan='free', plan_expires_at=NULL WHERE id=?", (user_id,))
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "Obuna muddati tugadi",
         f"{old_plan.upper()} obunangiz muddati tugadi va FREE rejaga o'tkazildingiz. "
         f"Qayta faollashtirish uchun yangi to'lov qiling.", "info")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(
            user_id, "Obuna muddati tugadi",
            f"{old_plan.upper()} obunangiz tugadi. Qayta faollashtiring.", "/pricing"
        )
    except Exception:
        pass
    log_action(user_id, "plan_auto_downgraded", details=f"from:{old_plan}")
    return True


def buy_course_with_coins(user_id: int, course_id: int, override_cost: int = None) -> tuple[bool, str]:
    """Pulik kursni code tangasiga sotib olish. Sarflangan coin G'azna jamg'armasiga tushadi.
    Pro/Cyber Pro/VIP/MAXSUS foydalanuvchilar uchun BEPUL (avtomatik yoziladi, CODE yechilmaydi)."""
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        return False, "Kurs topilmadi."
    user = query_one("SELECT role, plan FROM users WHERE id=?", (user_id,))
    existing = query_one("SELECT id FROM enrollments WHERE user_id=? AND course_id=?", (user_id, course_id))
    if existing:
        return False, "Siz bu kursga allaqachon yozilgansiz."

    # Tariflar olib tashlangan — endi hamma "cheksiz" tarif huquqiga ega
    is_unlimited_plan = True
    default_cost = course.get("code_price") or get_price("paid_course_code_default")
    cost = override_cost if override_cost is not None else default_cost
    if default_cost == 0 or is_unlimited_plan:
        execute("INSERT OR IGNORE INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                (user_id, course_id))
        log_action(user_id, "buy_course_code_free_plan" if is_unlimited_plan else "buy_course_free",
                   details=f"course:{course_id}")
        return True, "Rejangiz doirasida bepul yozildingiz!" if is_unlimited_plan else "Bepul kurs"

    ok, msg = spend_coins(user_id, cost, "buy_course", course_id)
    if not ok:
        return False, msg
    execute("INSERT OR IGNORE INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
            (user_id, course_id))
    log_action(user_id, "buy_course_code", details=f"course:{course_id},cost:{cost}")
    _treasury_fund_in(cost, "buy_course", user_id)
    return True, f"Kursga muvaffaqiyatli yozildingiz! ({cost:,} code sarflandi)"


def ensure_ai_access(user_id: int) -> tuple[bool, str]:
    """
    AI yordamchidan foydalanish huquqini tekshiradi/yangilaydi.

    - Pro / Cyber Pro / VIP / MAXSUS (hacker) foydalanuvchilar uchun cheksiz.
    - FREE foydalanuvchilar uchun HAFTALIK obuna: 1 hafta uchun bir marta
      `ai_weekly_price_code` (standart 1 CODE) yechiladi. Muddat ichida
      istalgancha xabar yozish mumkin — har xabar uchun alohida to'lov YO'Q.
    - Haftalik muddat tugagach, keyingi AI so'rovida avtomatik ravishda yana
      1 haftalik to'lov yechishga urinamiz ("avto to'lov"). Agar balansda
      yetarli CODE bo'lmasa — AI bloklanadi va foydalanuvchiga CODE
      sotib olish taklif qilinadi.

    Qaytaradi: (ruxsat_bormi: bool, xabar: str)
    """
    import datetime
    user = query_one("SELECT plan, code_balance, ai_sub_expires_at FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."

    # Tariflar olib tashlangan — endi hamma bepul va cheksiz
    return True, "pro"
    now = datetime.datetime.now()
    expires = None
    raw = user.get("ai_sub_expires_at")
    if raw:
        try:
            expires = datetime.datetime.fromisoformat(raw)
        except (ValueError, TypeError):
            expires = None

    if expires and now < expires:
        return True, "active"

    # Obuna muddati tugagan (yoki hali umuman obuna bo'lmagan) — avtomatik
    # haftalik to'lovni yechishga urinamiz.
    if price <= 0:
        new_expires = (now + datetime.timedelta(days=7)).isoformat()
        execute("UPDATE users SET ai_sub_expires_at=? WHERE id=?", (new_expires, user_id))
        return True, "free"

    ok, msg = spend_coins(user_id, price, "ai_weekly_sub")
    if not ok:
        return False, (
            f"AI yordamchidan foydalanish uchun haftalik {price:,} CODE kerak, "
            f"lekin balansingizda yetarli mablag' yo'q. Iltimos, CODE tanga sotib oling va qayta urinib ko'ring."
        )

    new_expires = (now + datetime.timedelta(days=7)).isoformat()
    execute("UPDATE users SET ai_sub_expires_at=? WHERE id=?", (new_expires, user_id))
    _treasury_fund_in(price, "ai_weekly_sub", user_id)
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "AI obuna yangilandi ⚡",
         f"AI yordamchidan foydalanish uchun {price:,} CODE yechildi. "
         f"Endi {new_expires[:10]} sanagacha AI'dan cheksiz foydalanishingiz mumkin.", "info")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(
            user_id, "AI obuna yangilandi ⚡",
            f"{price:,} CODE yechildi. Yana 7 kun AI'dan cheksiz foydalanasiz.", "/ai"
        )
    except Exception:
        pass
    return True, "renewed"


# ============================================================
# YANGI AI IQTISODIYOTI (v50) — ikkita alohida "havza":
#   1) ensure_ai_access_code_help — "kod yozish" AI yordami, HAR BIR
#      so'rov uchun 2 CODE (mashq izohi + AI orqali tekshirish).
#   2) ensure_ai_access_general   — oddiy savol-javob (umumiy AI
#      yordamchi, shaxsiy tavsiyalar), FREE foydalanuvchi uchun
#      kuniga 3 marta bepul.
# Pro/Cyber Pro/VIP/MAXSUS va admin/mentor/super_admin — ikkalasida
# ham CHEKSIZ va BEPUL.
# ============================================================
AI_CODE_HELP_PRICE = 2
AI_GENERAL_DAILY_FREE = 3
AI_BOOST_2X_PRICE = 5   # kunlik limitni 2 baravar (masalan 3->6) oshiradi, FAQAT o'sha kun uchun
AI_BOOST_5X_PRICE = 25  # kunlik limitni 5 baravar (masalan 3->15) oshiradi, FAQAT o'sha kun uchun


def _is_unlimited_ai_user(user: dict) -> bool:
    """Tariflar olib tashlangan — endi barcha foydalanuvchilar cheksiz AI'dan
    foydalanadi."""
    return True


def buy_ai_daily_boost(user_id: int, multiplier: int) -> tuple[bool, str]:
    """Kunlik AI limitini vaqtinchalik (FAQAT bugun uchun) oshiradi.
    multiplier: 2 (5 CODE) yoki 5 (25 CODE).

    MUHIM (tuzatilgan race condition): avval boost_multiplier ALOHIDA SELECT
    bilan tekshirilib, keyin CODE yechilib, SO'NGRA ALOHIDA (shartsiz) UPDATE
    bilan o'rnatilardi — ikkita deyarli bir vaqtdagi xarid ikkalasi ham
    "hali past" holatni o'qib, ikkalasi ham CODE to'lashi mumkin edi, lekin
    oxirida boost_multiplier faqat BITTA qiymatga o'rnatilib qolardi (foyda
    bitta, to'lov ikkita marta). Endi avval joy ATOMIK "band qilinadi"
    (UPDATE...WHERE boost_multiplier < multiplier), FAQAT shundan keyin CODE
    yechiladi — ikkinchi so'rov CODE to'lashdan OLDIN, band qilish
    bosqichidayoq rad etiladi."""
    import datetime
    user = query_one("SELECT role, plan FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if _is_unlimited_ai_user(user):
        return False, "Sizda allaqachon cheksiz AI huquqi bor — limit oshirish shart emas."
    if multiplier not in (2, 5):
        return False, "Noto'g'ri ko'paytiruvchi."
    price = AI_BOOST_2X_PRICE if multiplier == 2 else AI_BOOST_5X_PRICE

    today = datetime.date.today().isoformat()
    previous = query_one("SELECT boost_multiplier FROM ai_daily_usage WHERE user_id=? AND usage_date=?",
                         (user_id, today))
    previous_mult = previous["boost_multiplier"] if previous and previous["boost_multiplier"] else 1

    claimed = query_one(
        "INSERT INTO ai_daily_usage (user_id, usage_date, count, boost_multiplier) VALUES (?, ?, 0, ?) "
        "ON CONFLICT(user_id, usage_date) DO UPDATE SET boost_multiplier=? "
        "WHERE COALESCE(ai_daily_usage.boost_multiplier, 1) < ? "
        "RETURNING boost_multiplier",
        (user_id, today, multiplier, multiplier, multiplier)
    )
    if not claimed:
        current = query_one("SELECT boost_multiplier FROM ai_daily_usage WHERE user_id=? AND usage_date=?",
                            (user_id, today))
        current_mult = current["boost_multiplier"] if current and current["boost_multiplier"] else 1
        return False, f"Bugungi limitingiz allaqachon {current_mult}x holatda."

    ok, msg = spend_coins(user_id, price, f"ai_boost_{multiplier}x")
    if not ok:
        # Joy band qilingan edi, lekin to'lov muvaffaqiyatsiz — bandlikni
        # bekor qilamiz (faqat hali BIZ o'rnatgan qiymatda bo'lsa).
        execute(
            "UPDATE ai_daily_usage SET boost_multiplier=? "
            "WHERE user_id=? AND usage_date=? AND boost_multiplier=?",
            (previous_mult, user_id, today, multiplier)
        )
        return False, f"Limitni {multiplier}x oshirish uchun {price} CODE kerak, lekin balansingizda yetarli mablag' yo'q."

    try:
        _treasury_fund_in(price, f"ai_boost_{multiplier}x", user_id)
    except Exception:
        pass
    extra = (AI_GENERAL_DAILY_FREE * multiplier) - AI_GENERAL_DAILY_FREE
    return True, f"Bugungi AI limitingiz {multiplier}x oshirildi! (+{extra} qo'shimcha so'rov)"


def ensure_ai_access_code_help(user_id: int) -> tuple[bool, str]:
    """"Kod yozish" AI yordami — har bir so'rov uchun 2 CODE.
    Pro+ va admin/mentor — cheksiz va bepul."""
    user = query_one("SELECT role, plan, code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if _is_unlimited_ai_user(user):
        return True, "unlimited"

    ok, msg = spend_coins(user_id, AI_CODE_HELP_PRICE, "ai_code_help")
    if not ok:
        return False, (
            f"Kod bo'yicha AI yordamidan foydalanish uchun {AI_CODE_HELP_PRICE} CODE kerak, "
            f"lekin balansingizda yetarli mablag' yo'q. CODE tanga sotib oling yoki Pro rejaga o'ting "
            f"(Pro'da bu — bepul va cheksiz)."
        )
    try:
        _treasury_fund_in(AI_CODE_HELP_PRICE, "ai_code_help", user_id)
    except Exception:
        pass
    return True, "paid"


def ensure_ai_access_general(user_id: int) -> tuple[bool, str]:
    """Oddiy savol-javob (umumiy AI yordamchi, tavsiyalar) — FREE
    foydalanuvchi uchun kuniga 3 marta bepul. Pro+ va admin/mentor — cheksiz.

    MUHIM (tuzatilgan race condition): limit avval ALOHIDA SELECT bilan
    tekshirilib, keyin ALOHIDA INSERT/UPDATE bilan oshirilardi — ikkita
    deyarli bir vaqtdagi AI so'rovi (masalan ikkita brauzer tabida) HALI
    oshirilmagan hisobni o'qib, ikkalasi ham "limit hali yetarli" deb
    xulosa qilishi va limitdan ko'proq bepul so'rov yuborishi mumkin edi
    (haqiqiy AI API xarajati bilan). Endi tekshirish+oshirish BITTA
    atomik UPSERT bilan: `ON CONFLICT ... DO UPDATE ... WHERE count < limit`
    faqat limit hali yetarli bo'lsa qatorni o'zgartiradi va RETURNING orqali
    buni bildiradi."""
    import datetime
    user = query_one("SELECT role, plan FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."
    if _is_unlimited_ai_user(user):
        return True, "unlimited"

    today = datetime.date.today().isoformat()
    row = query_one(
        "INSERT INTO ai_daily_usage (user_id, usage_date, count) VALUES (?, ?, 1) "
        "ON CONFLICT(user_id, usage_date) DO UPDATE SET count = ai_daily_usage.count + 1 "
        "WHERE ai_daily_usage.count < ? * COALESCE(ai_daily_usage.boost_multiplier, 1) "
        "RETURNING count, boost_multiplier",
        (user_id, today, AI_GENERAL_DAILY_FREE)
    )
    if not row:
        current = query_one("SELECT count, boost_multiplier FROM ai_daily_usage WHERE user_id=? AND usage_date=?",
                            (user_id, today))
        boost = current["boost_multiplier"] if current and current["boost_multiplier"] else 1
        effective_limit = AI_GENERAL_DAILY_FREE * boost
        return False, (
            f"Kunlik bepul AI limitingiz ({effective_limit} ta so'rov) tugadi. "
            f"Ertaga qayta urinib ko'ring, limitni sotib oling (CODE Tangalar sahifasida) yoki Pro rejaga o'tib cheksiz foydalaning."
        )
    # MUHIM: query_one() commit() qilmaydi (faqat execute() qiladi) — yuqoridagi
    # atomik UPSERT'dan keyin hech qanday execute() chaqirilmasa, o'zgarish
    # HECH QACHON saqlanmaydi (ulanish yopilganda sukut bo'yicha ROLLBACK
    # bo'ladi). spend_coins() kabi funksiyalarda bu muammo yo'q, chunki ular
    # UPDATE...RETURNING'dan keyin har doim yana bitta execute() chaqiradi
    # (masalan tranzaksiya logini yozish uchun), shu commit() UPDATE'ni ham
    # birga saqlab yuboradi. Bu yerda bunday keyingi yozuv yo'q — shuning
    # uchun aniq commit() kerak.
    get_db().commit()
    boost = row["boost_multiplier"] if row["boost_multiplier"] else 1
    remaining = (AI_GENERAL_DAILY_FREE * boost) - row["count"]
    return True, f"free:{remaining}"


def transfer_coins(from_user_id: int, to_user_id: int, amount: int) -> tuple[bool, str]:
    """
    Foydalanuvchidan-foydalanuvchiga code tangasi o'tkazadi.
    Oddiy (free) foydalanuvchidan har bir o'tkazmadan komissiya olinadi
    (pricing_settings.coin_transfer_fee_percent, default 5%).
    Pro foydalanuvchi uchun komissiya 0%.
    Komissiya G'azna jamg'armasiga tushadi.
    """
    if amount <= 0:
        return False, "Miqdor musbat bo'lishi kerak."
    if from_user_id == to_user_id:
        return False, "O'zingizga tanga o'tkaza olmaysiz."

    sender = query_one("SELECT id, plan, code_balance FROM users WHERE id=?", (from_user_id,))
    receiver = query_one("SELECT id, is_blocked FROM users WHERE id=?", (to_user_id,))
    if not sender:
        return False, "Jo'natuvchi topilmadi."
    if not receiver:
        return False, "Qabul qiluvchi foydalanuvchi topilmadi."
    if receiver.get("is_blocked"):
        return False, "Bu foydalanuvchi bloklangan, tanga o'tkazib bo'lmaydi."

    # Tariflar olib tashlangan — o'tkazma solig'i endi hech kimdan olinmaydi
    is_pro = True
    fee_percent = 0 if is_pro else get_price("coin_transfer_fee_percent")
    fee_amount = (amount * fee_percent) // 100
    total_cost = amount + fee_amount

    balance = sender.get("code_balance") or 0
    if balance < total_cost:
        return False, (
            f"Yetarli code tangasi yo'q. Kerak: {total_cost:,} "
            f"(o'tkazma {amount:,} + komissiya {fee_amount:,}), mavjud: {balance:,}"
        )

    ok, msg = spend_coins(from_user_id, total_cost, "transfer_out", ref_id=to_user_id)
    if not ok:
        return False, msg
    add_coins(to_user_id, amount, "transfer_in", ref_id=from_user_id)

    execute(
        """INSERT INTO coin_transfers (from_user_id, to_user_id, amount_sent, fee_amount, amount_received)
           VALUES (?,?,?,?,?)""",
        (from_user_id, to_user_id, total_cost, fee_amount, amount)
    )
    log_action(from_user_id, "coin_transfer", details=f"to:{to_user_id},amount:{amount},fee:{fee_amount}")

    if fee_amount > 0:
        _treasury_fund_in(fee_amount, "transfer_fee", from_user_id)
        return True, f"{amount:,} CODE jo'natildi (komissiya: {fee_amount:,} CODE)."
    return True, f"{amount:,} CODE jo'natildi (Pro: komissiyasiz)."


def get_transactions(user_id: int, limit: int = 20):
    return __import__('db').query_all(
        "SELECT * FROM code_transactions WHERE user_id=? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )


def get_leaderboard(limit: int = 20):
    """Faqat student va pro foydalanuvchilarni qaytaradi (admin/mentor chiqarilmaydi)."""
    return __import__('db').query_all(
        """SELECT u.id, u.ism, u.familiya, u.avatar, u.level, u.plan,
                  u.code_balance,
                  COALESCE(ur.total_score,0) as total_score,
                  COALESCE(ur.courses_done,0) as courses_done,
                  COALESCE(ur.rank_position,0) as rank_position
           FROM users u LEFT JOIN user_ratings ur ON ur.user_id=u.id
           WHERE u.is_blocked=0 AND u.role NOT IN ('admin','mentor')
           ORDER BY COALESCE(ur.total_score,0) DESC, u.xp DESC
           LIMIT ?""",
        (limit,)
    )


def _update_rating(user_id: int):
    from db import query_all
    courses_done = query_one(
        "SELECT COUNT(*) c FROM enrollments WHERE user_id=? AND progress_percent=100", (user_id,)
    )["c"]
    tests_passed = query_one(
        "SELECT COUNT(*) c FROM test_attempts WHERE user_id=? AND score * 100.0 / NULLIF(total,0) >= 60",
        (user_id,)
    )["c"]
    user = query_one("SELECT xp, code_balance FROM users WHERE id=?", (user_id,))
    total = (user["xp"] or 0) + (courses_done * 500) + (tests_passed * 100)
    execute(
        """INSERT INTO user_ratings (user_id, total_score, courses_done, tests_passed, updated_at)
           VALUES (?,?,?,?, datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET
               total_score=excluded.total_score,
               courses_done=excluded.courses_done,
               tests_passed=excluded.tests_passed,
               updated_at=excluded.updated_at""",
        (user_id, total, courses_done, tests_passed)
    )
    # Pozitsiyalarni yangilash
    execute("""
        UPDATE user_ratings SET rank_position = (
            SELECT COUNT(*) + 1 FROM user_ratings r2
            WHERE r2.total_score > user_ratings.total_score
        )
    """)
