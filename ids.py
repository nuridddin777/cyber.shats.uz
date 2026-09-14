"""
CYBER SHATS — User ID va Auktsion moduli
7 xonali unikal ID tizimi, premium IDlar (bazada saqlanadi, admin to'liq boshqaradi), auktsion
"""
import random
import string
from db import query_one, query_all, execute, log_action
from config import Config

# ID auksioni yopilib, Random ID tizimi kelgani sababli — ANIQ (o'zi tanlagan)
# ID o'zgartirish endi qat'iy 500 CODE turadi.
REGULAR_ID_CHANGE_PRICE = 500


def _record_id_change(user_id: int, new_custom_id: str, obtained_via: str):
    """ID TARIXI: eskisini "released" deb belgilaydi (Random/bozorga
    QAYTA TUSHMAYDI, admin ataylab qaytarmasa), yangisini "current" deb
    yozadi. Bu — profildagi "ID koleksiyasi" uchun asosiy funksiya."""
    old = query_one("SELECT custom_id FROM users WHERE id=?", (user_id,))
    old_id = old["custom_id"] if old else None
    if old_id and old_id != new_custom_id:
        execute("UPDATE user_id_history SET status='released', released_at=datetime('now') "
                "WHERE user_id=? AND custom_id=? AND status='current'", (user_id, old_id))
    execute("INSERT INTO user_id_history (user_id, custom_id, obtained_via, status) VALUES (?,?,?,'current')",
            (user_id, new_custom_id, obtained_via))


def get_user_id_history(user_id: int):
    return query_all(
        "SELECT * FROM user_id_history WHERE user_id=? ORDER BY obtained_at DESC", (user_id,))


def is_id_in_anyones_history(custom_id: str) -> bool:
    """ID hech kimning tarixida (hozirgi yoki avvalgi) bo'lsa — va admin
    uni ATAYLAB muomalaga qaytarmagan bo'lsa — Random/bozorga tushmaydi."""
    row = query_one(
        "SELECT id FROM user_id_history WHERE custom_id=? AND released_to_pool=0 LIMIT 1", (custom_id,))
    return row is not None


# 4 xil raqam ID narxlari — avtomatik narx aniqlash uchun standart jadval
# (Admin alohida ID uchun bazada maxsus narx belgilashi mumkin, bu faqat fallback)
ID_PRICE_RULES = {
    "quad4": 40_000,   # 4 ta bir xil raqam
    "quad5": 50_000,   # 5 ta bir xil raqam
    "quad6": 60_000,   # 6 ta bir xil raqam
    "quad7": 100_000,  # 7 ta bir xil raqam
    "sequential": 120_000,  # 1234567 kabi
}


def _auto_id_type_and_price(custom_id: str) -> tuple[str, int]:
    """Bazada topilmagan yangi ID uchun avtomatik tur va narx aniqlaydi."""
    digits = list(custom_id)
    for count in [7, 6, 5, 4]:
        for d in "0123456789":
            if digits.count(d) >= count:
                key = f"quad{count}"
                return key, ID_PRICE_RULES[key]
    return "normal", 0


def _id_type_and_price(custom_id: str) -> tuple[str, int]:
    """ID turi va narxini aniqlaydi: avval bazadan, topilmasa avtomatik."""
    row = query_one("SELECT id_type, base_price FROM premium_ids WHERE custom_id=?", (custom_id,))
    if row:
        return row["id_type"], row["base_price"]
    return _auto_id_type_and_price(custom_id)


def generate_unique_id() -> str:
    """Yangi unikal 7 xonali ID yaratadi (avto-registratsiyada ishlatiladi)."""
    for _ in range(1000):
        num = random.randint(1_000_000, 9_999_999)
        cid = str(num)
        # Bazada premium sifatida ro'yxatdan o'tgan IDlarni o'tkazib yuborish
        is_premium = query_one("SELECT id FROM premium_ids WHERE custom_id=?", (cid,))
        if is_premium:
            continue
        # 4+ bir xil raqam bo'lsa ham premium hisoblanadi — avtomatik berilmasin
        has_quad = any(cid.count(d) >= 4 for d in "0123456789")
        if has_quad:
            continue
        # Mavjudligini tekshir
        exists = query_one("SELECT id FROM users WHERE custom_id=?", (cid,))
        if not exists:
            return cid
    # Fallback
    return str(random.randint(1_000_000, 9_999_999))


def set_user_id(user_id: int, new_custom_id: str) -> tuple[bool, str]:
    """Foydalanuvchi o'zi ANIQ ID tanlab o'zgartiradi (agar ID bo'sh bo'lsa).
    DIQQAT: avval narx o'zgartirish soniga qarab oshib borardi (1->2->3
    CODE). Endi ID auksioni yopilib, o'rniga Random ID tizimi kelgani
    sababli, ANIQ ID tanlash — qat'iy 500 CODE turadi (tasodifiy ID
    aylantirishdan farqli, bu yerda foydalanuvchi ISTAGAN raqamni tanlaydi)."""
    from coins import spend_coins, refund_coins
    existing = query_one("SELECT id FROM users WHERE custom_id=?", (new_custom_id,))
    if existing:
        return False, "Bu ID allaqachon band. Boshqa ID tanlang."
    if is_id_in_anyones_history(new_custom_id):
        return False, "Bu ID avval kimgadir tegishli bo'lgan va hali muomalaga qaytarilmagan — boshqa ID tanlang."
    price = REGULAR_ID_CHANGE_PRICE

    ok, msg = spend_coins(user_id, price, "id_change")
    if not ok:
        return False, f"ID o'zgartirish uchun {price} CODE kerak, lekin balansingiz yetarli emas."

    try:
        _record_id_change(user_id, new_custom_id, "tanlab_ozgartirdi")
        execute("UPDATE users SET custom_id=?, id_change_count=id_change_count+1 WHERE id=?",
                (new_custom_id, user_id))
    except Exception as e:
        refund_coins(user_id, price, "id_change_failed")
        import logging
        logging.getLogger("cybershats").error(f"set_user_id xato, CODE qaytarildi: {e}")
        return False, "Texnik xatolik yuz berdi. CODE'ingiz balansingizga qaytarildi, qaytadan urinib ko'ring."

    return True, f"ID muvaffaqiyatli o'zgartirildi! ({price} CODE yechildi)"


def get_premium_ids_list():
    """Bazadagi barcha premium IDlar va ularning holati (admin tomonidan qo'shilgan/tahrirlangan)."""
    return query_all("SELECT * FROM premium_ids ORDER BY created_at DESC")


def init_premium_ids():
    """Eski versiyalar bilan moslik uchun qoldirilgan — endi premium IDlar to'liq
    admin panel orqali (admin_create_premium_id) qo'shiladi va migrate_v2.py orqali seed qilinadi."""
    pass


def admin_create_premium_id(custom_id: str, base_price: int, id_type: str = "custom") -> tuple[bool, str]:
    """Admin yangi premium ID qo'shadi (istalgan 7 xonali raqam + narx)."""
    custom_id = custom_id.strip()
    if len(custom_id) != 7 or not custom_id.isdigit():
        return False, "ID 7 ta raqamdan iborat bo'lishi kerak."
    if base_price < 0:
        return False, "Narx manfiy bo'lishi mumkin emas."
    existing = query_one("SELECT id FROM premium_ids WHERE custom_id=?", (custom_id,))
    if existing:
        return False, "Bu ID allaqachon premium ro'yxatda mavjud."
    owned = query_one("SELECT id FROM users WHERE custom_id=?", (custom_id,))
    if owned:
        return False, "Bu ID allaqachon bir foydalanuvchiga tegishli."
    execute(
        "INSERT INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,'available')",
        (custom_id, id_type, base_price)
    )
    return True, f"#{custom_id} premium ID {base_price:,} code narx bilan qo'shildi."


def admin_update_premium_id_price(custom_id: str, base_price: int) -> tuple[bool, str]:
    """Admin mavjud premium IDning narxini o'zgartiradi."""
    if base_price < 0:
        return False, "Narx manfiy bo'lishi mumkin emas."
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid:
        return False, "Bu ID mavjud emas."
    execute("UPDATE premium_ids SET base_price=? WHERE custom_id=?", (base_price, custom_id))
    return True, f"#{custom_id} narxi {base_price:,} code ga o'zgartirildi."


def admin_delete_premium_id(custom_id: str) -> tuple[bool, str]:
    """Admin premium IDni ro'yxatdan o'chiradi (faqat sotilmagan/auktsionda bo'lmaganlarni)."""
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid:
        return False, "Bu ID mavjud emas."
    if pid["status"] != "available":
        return False, "Faqat 'bo'sh' holatdagi IDlarni o'chirish mumkin."
    execute("DELETE FROM premium_ids WHERE custom_id=?", (custom_id,))
    return True, f"#{custom_id} premium ID ro'yxatdan o'chirildi."


def buy_premium_id(user_id: int, custom_id: str) -> tuple[bool, str]:
    """Admin tomonidan tayinlangan premium IDni code bilan sotib olish.
    To'langan code g'azna jamg'armasiga tushadi."""
    from coins import spend_coins, refund_coins
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid:
        return False, "Bu ID mavjud emas."
    if pid["status"] != "available":
        return False, "Bu ID allaqachon band yoki auktsiyonda."
    price = pid["base_price"]
    ok, msg = spend_coins(user_id, price, "buy_premium_id", pid["id"])
    if not ok:
        return False, msg
    try:
        import datetime
        execute("UPDATE premium_ids SET status='sold', owner_user_id=?, sold_at=? WHERE custom_id=?",
                (user_id, datetime.datetime.now().isoformat(), custom_id))
        _record_id_change(user_id, custom_id, "chiroyli_id_sotib_oldi")
        execute("UPDATE users SET custom_id=? WHERE id=?", (custom_id, user_id))
        # Sotuvdan kelgan daromad g'azna jamg'armasiga tushadi
        from treasury import add_id_auction_revenue
        add_id_auction_revenue(price, user_id, custom_id)
    except Exception as e:
        refund_coins(user_id, price, "buy_premium_id_failed", pid["id"])
        import logging
        logging.getLogger("cybershats").error(f"buy_premium_id xato, CODE qaytarildi: {e}")
        return False, "Texnik xatolik yuz berdi. CODE'ingiz balansingizga qaytarildi, qaytadan urinib ko'ring."
    return True, f"ID #{custom_id} muvaffaqiyatli sotib olindi!"


def get_active_auctions():
    return query_all(
        """SELECT a.*, p.id_type, p.base_price,
                  u.ism as bidder_ism, u.familiya as bidder_familiya
           FROM id_auctions a
           JOIN premium_ids p ON p.id=a.premium_id_id
           LEFT JOIN users u ON u.id=a.current_bidder_id
           WHERE a.status='active' AND a.ends_at > datetime('now')
           ORDER BY a.ends_at ASC"""
    )


def place_bid(user_id: int, auction_id: int, bid_amount: int) -> tuple[bool, str]:
    """Auktsiyonda taklif qo'yish."""
    from coins import spend_coins, add_coins
    auction = query_one("SELECT * FROM id_auctions WHERE id=? AND status='active'", (auction_id,))
    if not auction:
        return False, "Auktsion topilmadi yoki tugagan."
    min_bid = max(auction["current_bid"] + 1000, auction["start_price"])
    if bid_amount < min_bid:
        return False, f"Minimal taklif: {min_bid:,} code"
    # Avvalgi bidder puli qaytarilsin
    if auction["current_bidder_id"] and auction["current_bidder_id"] != user_id:
        add_coins(auction["current_bidder_id"], auction["current_bid"], "auction_refund", auction_id)
    # Yangi bidder
    ok, msg = spend_coins(user_id, bid_amount, "auction_bid", auction_id)
    if not ok:
        return False, msg
    execute("UPDATE id_auctions SET current_bid=?, current_bidder_id=? WHERE id=?",
            (bid_amount, user_id, auction_id))
    execute("INSERT INTO auction_bids (auction_id, user_id, bid_amount) VALUES (?,?,?)",
            (auction_id, user_id, bid_amount))
    return True, f"Taklif qabul qilindi: {bid_amount:,} code"


def admin_close_all_bidding_auctions() -> tuple[bool, str]:
    """ID auksioni (oldingi taklif-berish uslubi) butunlay yopiladi.
    Faol auktsionlardagi joriy g'olib takliflari to'liq qaytariladi
    (adolatli — ular hali ID olmagan, pulini yo'qotmasligi kerak)."""
    from coins import add_coins
    active = query_all("SELECT * FROM id_auctions WHERE status='active'")
    refunded = 0
    for a in active:
        if a["current_bidder_id"] and a["current_bid"]:
            add_coins(a["current_bidder_id"], a["current_bid"], "auction_closed_refund", a["id"])
            refunded += 1
        execute("UPDATE id_auctions SET status='cancelled' WHERE id=?", (a["id"],))
        execute("UPDATE premium_ids SET status='available' WHERE id=?", (a["premium_id_id"],))
    return True, f"{len(active)} ta faol auktsion yopildi, {refunded} ta ishtirokchiga puli qaytarildi."


def finalize_auction(auction_id: int):
    """Tugagan auktsionni yakunlash (cron yoki admin tugmasi orqali).
    G'olibning to'lagani g'azna jamg'armasiga tushadi."""
    import datetime
    auction = query_one("SELECT * FROM id_auctions WHERE id=?", (auction_id,))
    if not auction or auction["status"] != "active":
        return
    execute("UPDATE id_auctions SET status='ended' WHERE id=?", (auction_id,))
    if auction["current_bidder_id"]:
        execute("UPDATE premium_ids SET status='sold', owner_user_id=?, sold_at=? WHERE custom_id=?",
                (auction["current_bidder_id"], datetime.datetime.now().isoformat(), auction["custom_id"]))
        execute("UPDATE users SET custom_id=? WHERE id=?",
                (auction["custom_id"], auction["current_bidder_id"]))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (auction["current_bidder_id"],
                 f"Auktsion g'olibi!",
                 f"Siz #{auction['custom_id']} ID auktsionida g'olib bo'ldingiz!",
                 "success"))
        try:
            import webpush_mod
            webpush_mod.send_push_to_user(
                auction["current_bidder_id"], "Auktsion g'olibi! 🏆",
                f"Siz #{auction['custom_id']} ID auktsionida g'olib bo'ldingiz!", "/profile"
            )
        except Exception:
            pass
        # G'olibning to'lagani g'azna jamg'armasiga tushadi
        from treasury import add_id_auction_revenue
        add_id_auction_revenue(auction["current_bid"], auction["current_bidder_id"], auction["custom_id"])
    execute("UPDATE premium_ids SET status='available' WHERE custom_id=? AND owner_user_id IS NULL",
            (auction["custom_id"],))


# =================================================================
# VIP MAXSUS ID'LAR — 1 xonali raqamlar (0-9), 10 ta, faqat admin beradi.
# Auksion yo'q, sotuv yo'q — faqat qo'lda admin tomonidan tayinlanadi.
# =================================================================

def get_vip_ids_list():
    """Barcha 10 ta VIP ID holatini qaytaradi (egasi ma'lumoti bilan)."""
    return query_all(
        """SELECT v.*, u.ism, u.familiya, u.email
           FROM vip_ids v
           LEFT JOIN users u ON u.id = v.owner_user_id
           ORDER BY v.digit ASC"""
    )


def assign_vip_id(admin_id: int, digit: str, user_id: int) -> tuple[bool, str]:
    """Admin tomonidan VIP ID (0-9) foydalanuvchiga tayinlanadi.
    Foydalanuvchining oddiy custom_id'i shu bitta raqamga almashtiriladi."""
    digit = str(digit).strip()
    if digit not in "0123456789" or len(digit) != 1:
        return False, "SHATS CYBER PRO ID faqat 0-9 oralig'idagi bitta raqam bo'lishi mumkin."
    vip_row = query_one("SELECT * FROM vip_ids WHERE digit=?", (digit,))
    if not vip_row:
        return False, "Bunday SHATS CYBER PRO ID topilmadi."
    if vip_row["status"] == "assigned":
        return False, f"SHATS CYBER PRO ID '{digit}' allaqachon band."
    user = query_one("SELECT id, custom_id FROM users WHERE id=?", (user_id,))
    if not user:
        return False, "Foydalanuvchi topilmadi."

    import datetime
    old_cid = user["custom_id"]
    execute(
        "UPDATE vip_ids SET status='assigned', owner_user_id=?, assigned_by=?, assigned_at=? WHERE digit=?",
        (user_id, admin_id, datetime.datetime.now().isoformat(), digit)
    )
    execute("UPDATE users SET custom_id=? WHERE id=?", (digit, user_id))
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (user_id, "SHATS CYBER PRO ID berildi! 🔥",
         f"Sizga maxsus SHATS CYBER PRO ID '#{digit}' tayinlandi! Eski ID: #{old_cid}", "success")
    )
    try:
        import webpush_mod
        webpush_mod.send_push_to_user(
            user_id, "SHATS CYBER PRO ID berildi! 🔥", f"Sizga maxsus SHATS CYBER PRO ID '#{digit}' tayinlandi!", "/profile"
        )
    except Exception:
        pass
    return True, f"SHATS CYBER PRO ID '#{digit}' foydalanuvchiga muvaffaqiyatli berildi."


def revoke_vip_id(digit: str) -> tuple[bool, str]:
    """VIP ID'ni egasidan qaytarib olish (yana 'available' qiladi)."""
    digit = str(digit).strip()
    vip_row = query_one("SELECT * FROM vip_ids WHERE digit=?", (digit,))
    if not vip_row or vip_row["status"] != "assigned":
        return False, "Bu SHATS CYBER PRO ID band emas."
    owner_id = vip_row["owner_user_id"]
    execute("UPDATE vip_ids SET status='available', owner_user_id=NULL, assigned_by=NULL, assigned_at=NULL WHERE digit=?",
            (digit,))
    if owner_id:
        # Foydalanuvchiga yangi oddiy ID beramiz (VIP ID'siz qolmasin)
        new_cid = generate_unique_id()
        execute("UPDATE users SET custom_id=? WHERE id=?", (new_cid, owner_id))
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (owner_id, "SHATS CYBER PRO ID qaytarib olindi",
             f"SHATS CYBER PRO ID '#{digit}' administrator tomonidan qaytarib olindi. Yangi ID: #{new_cid}", "info")
        )
    return True, f"SHATS CYBER PRO ID '#{digit}' bo'shatildi."


import re as _re


def admin_set_alphanumeric_id(admin_user_id: int, target_identifier: str, new_id: str) -> tuple[bool, str]:
    """FAQAT admin ishlatishi mumkin — oddiy foydalanuvchiga TAQIQLANGAN
    harflar aralash maxsus ID beradi (masalan 'SHATS-1', 'KING2026').
    Oddiy foydalanuvchilar hali ham FAQAT 7 xonali raqamli ID ishlatishi
    mumkin (set_user_id orqali) — bu funksiya shu cheklovni ATAYLAB
    chetlab o'tadi, chunki bu maxsus, faqat admin bera oladigan imtiyoz."""
    new_id = (new_id or "").strip().upper()
    if not (3 <= len(new_id) <= 16):
        return False, "Maxsus ID 3 dan 16 belgigacha bo'lishi kerak."
    if not _re.match(r'^[A-Z0-9\-_]+$', new_id):
        return False, "Faqat lotin harflari (A-Z), raqamlar, tire (-) va pastki chiziq (_) ruxsat etiladi."

    target = query_one("SELECT id, ism, familiya FROM users WHERE id=? OR custom_id=? OR email=?",
                       (target_identifier, target_identifier, target_identifier))
    if not target:
        return False, "Foydalanuvchi topilmadi (ID, maxsus ID yoki email kiriting)."

    existing = query_one("SELECT id FROM users WHERE custom_id=? AND id != ?", (new_id, target["id"]))
    if existing:
        return False, "Bu maxsus ID allaqachon band."

    execute("UPDATE users SET custom_id=? WHERE id=?", (new_id, target["id"]))
    _record_id_change(target["id"], new_id, "admin_berdi")
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (target["id"], "Sizga maxsus ID berildi! ✨",
             f"Super admin sizga maxsus ID berdi: #{new_id}", "success"))
    log_action(admin_user_id, "admin_set_alphanumeric_id",
              details=f"target:{target['id']},new_id:{new_id}")
    return True, f"«{target['familiya']} {target['ism']}» ga maxsus ID berildi: #{new_id}"


# =================================================================
# RANDOM ID AUKTSIONI — eski taklif-berish auktsioni o'rniga
# =================================================================
# ID o'zgartirish endi ODDIY tanlashda 500 CODE (qat'iy narx).
# "Random ID" — foydalanuvchi "aylantiradi", tizim tasodifiy 7 xonali ID
# taklif qiladi, uning "chiroyliligi"ga qarab 1 dan 1000 CODEgacha
# narxlanadi (chiroylimi — tekshiradigan evristika bilan).


def _score_random_id(digits: str) -> int:
    """ID qanchalik 'chiroyli' ekanini 0 dan taxminan 200 gacha ball bilan
    baholaydi (ko'proq — chiroyliroq/qimmatroq)."""
    score = 0
    distinct = len(set(digits))
    if distinct == 2:
        score += 40
    elif distinct == 3:
        score += 22
    elif distinct == 4:
        score += 9

    asc = all(int(digits[i + 1]) - int(digits[i]) == 1 for i in range(6))
    desc = all(int(digits[i]) - int(digits[i + 1]) == 1 for i in range(6))
    if asc or desc:
        score += 80

    if digits == digits[::-1]:
        score += 30

    max_run, cur_run = 1, 1
    for i in range(1, 7):
        if digits[i] == digits[i - 1]:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 1
    if max_run >= 4:
        score += 50
    elif max_run == 3:
        score += 20

    if digits.endswith('000') or digits.startswith('000') or digits.endswith('999') or digits.startswith('999'):
        score += 15

    return score


def _random_id_price(score: int) -> int:
    """Narx oralig'i: 700 CODE (eng oddiy ID) dan 1000 CODE (eng chiroyli
    ID) gacha — foydalanuvchi so'ragan yangi narx darajasi."""
    price = int(700 + score * 5)
    return max(700, min(1000, price))


def is_id_reserved(custom_id: str) -> bool:
    """ID hozir band qilinganmi (rezervatsiya muddati hali tugamagan)?"""
    row = query_one(
        "SELECT id FROM id_reservations WHERE custom_id=? AND status='active' "
        "AND datetime(expires_at) > datetime('now')", (custom_id,))
    return row is not None


def generate_random_id_offer() -> dict:
    """Tasodifiy, hali band bo'lmagan, kuratsiyalangan (premium_ids
    jadvalidagi) ro'yxatda bo'lmagan, hech kimning tarixida
    (released_to_pool=0 holda) bo'lmagan VA HOZIR REZERVATSIYADA
    bo'lmagan 7 xonali ID taklif qiladi."""
    for _ in range(60):
        digits = "".join(str(random.randint(0, 9)) for _ in range(7))
        if query_one("SELECT id FROM users WHERE custom_id=?", (digits,)):
            continue
        if query_one("SELECT id FROM premium_ids WHERE custom_id=?", (digits,)):
            continue
        if is_id_in_anyones_history(digits):
            continue
        if is_id_reserved(digits):
            continue
        score = _score_random_id(digits)
        price = _random_id_price(score)
        return {"custom_id": digits, "price": price, "score": score}
    # Juda kam ehtimol — 60 urinishda ham bo'sh ID topilmasa
    return {"custom_id": generate_unique_id(), "price": 1, "score": 0}


RESERVATION_HOURS = 48  # 2 kun


def reserve_random_id(user_id: int, custom_id: str, price: int) -> tuple[bool, str]:
    """Foydalanuvchi yoqqan, lekin CODE yetmagan Random ID'ni 48 soatga
    BEPUL band qilib qo'yadi. Har foydalanuvchida bir vaqtda faqat 1 ta
    faol band bo'lishi mumkin."""
    existing = query_one(
        "SELECT id FROM id_reservations WHERE user_id=? AND status='active' "
        "AND datetime(expires_at) > datetime('now')", (user_id,))
    if existing:
        return False, "Sizda allaqachon faol band qilingan ID bor. Avval o'shani sotib oling yoki bekor qiling."
    if query_one("SELECT id FROM users WHERE custom_id=?", (custom_id,)):
        return False, "Bu ID orada band bo'lib qolgan."
    if is_id_reserved(custom_id):
        return False, "Bu ID boshqa foydalanuvchi tomonidan allaqachon band qilingan."
    execute(
        "INSERT INTO id_reservations (user_id, custom_id, price, status, expires_at) "
        "VALUES (?,?,?,'active', datetime('now', ?))",
        (user_id, custom_id, price, f"+{RESERVATION_HOURS} hours")
    )
    return True, f"#{custom_id} sizga {RESERVATION_HOURS} soatga (2 kun) band qilindi! Shu muddatda CODE to'plab, sotib oling."


def get_active_reservation(user_id: int):
    return query_one(
        "SELECT * FROM id_reservations WHERE user_id=? AND status='active' "
        "AND datetime(expires_at) > datetime('now')", (user_id,))


def cancel_reservation(user_id: int, reservation_id: int) -> tuple[bool, str]:
    row = query_one("SELECT id FROM id_reservations WHERE id=? AND user_id=? AND status='active'",
                    (reservation_id, user_id))
    if not row:
        return False, "Band topilmadi."
    execute("UPDATE id_reservations SET status='cancelled' WHERE id=?", (reservation_id,))
    return True, "Band bekor qilindi."


def buy_reserved_id(user_id: int, reservation_id: int) -> tuple[bool, str]:
    """Band qilingan IDni endi haqiqiy sotib olish — confirm_random_id
    bilan bir xil narx/tarix mantig'idan foydalanadi."""
    res = query_one(
        "SELECT * FROM id_reservations WHERE id=? AND user_id=? AND status='active' "
        "AND datetime(expires_at) > datetime('now')", (reservation_id, user_id))
    if not res:
        return False, "Band muddati tugagan yoki topilmadi."
    ok, msg = confirm_random_id(user_id, res["custom_id"], res["price"])
    if ok:
        execute("UPDATE id_reservations SET status='completed' WHERE id=?", (reservation_id,))
    return ok, msg




def confirm_random_id(user_id: int, offered_id: str, expected_price: int) -> tuple[bool, str]:
    """Foydalanuvchi taklif qilingan tasodifiy IDni tasdiqlaganda chaqiriladi.
    Narx qayta serverda hisoblanadi (front-end'dan kelgan narxga ishonilmaydi).

    MUHIM (tuzatilgan JIDDIY XATO): avval CODE yechilgach, ID
    o'zgartirish qadami (_record_id_change + UPDATE) HIMOYASIZ edi.
    Agar ular xato bersa — foydalanuvchi CODE'ni YO'QOTAR, lekin ID
    o'zgarmasdi! Endi bu qadamlar try/except bilan o'ralgan — xato
    bo'lsa, CODE AVTOMATIK qaytariladi."""
    from coins import spend_coins, refund_coins
    if len(offered_id) != 7 or not offered_id.isdigit():
        return False, "Noto'g'ri ID formati."
    if query_one("SELECT id FROM users WHERE custom_id=?", (offered_id,)):
        return False, "Bu ID orada band bo'lib qolgan, qayta aylantiring."
    if query_one("SELECT id FROM premium_ids WHERE custom_id=?", (offered_id,)):
        return False, "Bu ID kuratsiyalangan ro'yxatda, alohida sotib olinadi."
    if is_id_in_anyones_history(offered_id):
        return False, "Bu ID orada band bo'lib qolgan, qayta aylantiring."

    real_price = _random_id_price(_score_random_id(offered_id))
    ok, msg = spend_coins(user_id, real_price, "random_id_roll")
    if not ok:
        return False, f"Bu ID uchun {real_price} CODE kerak, lekin balansingiz yetarli emas."

    try:
        _record_id_change(user_id, offered_id, "random_id")
        execute("UPDATE users SET custom_id=? WHERE id=?", (offered_id, user_id))
    except Exception as e:
        refund_coins(user_id, real_price, "random_id_roll_failed")
        import logging
        logging.getLogger("cybershats").error(f"confirm_random_id xato, CODE qaytarildi: {e}")
        return False, "Texnik xatolik yuz berdi. CODE'ingiz balansingizga qaytarildi, qaytadan urinib ko'ring."

    return True, f"Yangi ID o'rnatildi: #{offered_id} ({real_price} CODE yechildi)"


# =================================================================
# FOYDALANUVCHI O'Z ID'SINI SOTISHI — faqat Super Admin/G'azna sotib oladi
# =================================================================
def create_sell_offer(user_id: int, asking_price: int) -> tuple[bool, str]:
    """Foydalanuvchi joriy IDsini narx qo'yib sotuvga chiqaradi."""
    if asking_price < 1:
        return False, "Narx kamida 1 CODE bo'lishi kerak."
    user = query_one("SELECT custom_id FROM users WHERE id=?", (user_id,))
    if not user or not user["custom_id"]:
        return False, "Sizda hali ID mavjud emas."
    existing = query_one(
        "SELECT id FROM id_sell_offers WHERE user_id=? AND status IN ('pending','countered')", (user_id,))
    if existing:
        return False, "Sizda allaqachon faol sotuv taklifi bor."
    execute(
        "INSERT INTO id_sell_offers (user_id, custom_id, asking_price, status) VALUES (?,?,?,'pending')",
        (user_id, user["custom_id"], asking_price)
    )
    return True, f"ID #{user['custom_id']} {asking_price:,} CODEga sotuvga chiqarildi. Admin ko'rib chiqadi."


def get_user_sell_offer(user_id: int):
    return query_one(
        "SELECT * FROM id_sell_offers WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,))


def cancel_sell_offer(user_id: int, offer_id: int) -> tuple[bool, str]:
    offer = query_one("SELECT * FROM id_sell_offers WHERE id=? AND user_id=?", (offer_id, user_id))
    if not offer or offer["status"] not in ("pending", "countered"):
        return False, "Bekor qilinadigan taklif topilmadi."
    execute("UPDATE id_sell_offers SET status='cancelled', updated_at=datetime('now') WHERE id=?", (offer_id,))
    return True, "Sotuv taklifi bekor qilindi."


def user_respond_to_counter(user_id: int, offer_id: int, accept: bool) -> tuple[bool, str]:
    """Foydalanuvchi admin taklif qilgan (arzonroq) narxga rozi bo'ladimi yoki yo'q."""
    offer = query_one("SELECT * FROM id_sell_offers WHERE id=? AND user_id=? AND status='countered'",
                      (offer_id, user_id))
    if not offer:
        return False, "Javob beriladigan taklif topilmadi."
    if not accept:
        execute("UPDATE id_sell_offers SET status='rejected', updated_at=datetime('now') WHERE id=?", (offer_id,))
        return True, "Taklif rad etildi."
    return admin_complete_id_purchase(offer["handled_by"], offer_id, offer["counter_price"])


def get_pending_sell_offers():
    return query_all("""
        SELECT o.*, u.ism, u.familiya, u.custom_id as current_custom_id
        FROM id_sell_offers o JOIN users u ON u.id = o.user_id
        WHERE o.status IN ('pending','countered') ORDER BY o.created_at DESC
    """)


def admin_counter_offer(admin_id: int, offer_id: int, counter_price: int) -> tuple[bool, str]:
    """Super Admin/G'azna — foydalanuvchining so'ragan narxidan ARZONROQ narx taklif qiladi (savdolashish)."""
    offer = query_one("SELECT * FROM id_sell_offers WHERE id=? AND status='pending'", (offer_id,))
    if not offer:
        return False, "Faol taklif topilmadi."
    if counter_price < 1 or counter_price >= offer["asking_price"]:
        return False, "Taklif qilingan narx so'ralgan narxdan KAMROQ bo'lishi kerak."
    execute(
        "UPDATE id_sell_offers SET status='countered', counter_price=?, handled_by=?, updated_at=datetime('now') WHERE id=?",
        (counter_price, admin_id, offer_id)
    )
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (offer["user_id"], "ID sotuvingizga javob keldi 💬",
             f"Admin #{offer['custom_id']} uchun {counter_price:,} CODE taklif qildi (siz {offer['asking_price']:,} so'ragan edingiz).",
             "info"))
    return True, f"{counter_price:,} CODE taklif qilindi, foydalanuvchiga yuborildi."


def admin_accept_offer_at_asking(admin_id: int, offer_id: int, disposition: str = "random_pool",
                                 marketplace_price: int = None) -> tuple[bool, str]:
    """Admin/G'azna foydalanuvchi so'ragan narxning O'ZIGA rozi bo'lib, darhol sotib oladi."""
    offer = query_one("SELECT * FROM id_sell_offers WHERE id=? AND status='pending'", (offer_id,))
    if not offer:
        return False, "Faol taklif topilmadi."
    return admin_complete_id_purchase(admin_id, offer_id, offer["asking_price"], disposition, marketplace_price)


def admin_complete_id_purchase(admin_id: int, offer_id: int, final_price: int,
                               disposition: str = "random_pool", marketplace_price: int = None) -> tuple[bool, str]:
    """ID sotib olish savdosini yakunlaydi. `disposition` — admin sotib
    olingan ID bilan keyin nima qilishni TANLAYDI:
      - 'marketplace': ID chiroyli — kuratsiyalangan bozorga qo'shiladi,
        narxni ADMIN O'ZI belgilaydi (marketplace_price).
      - 'random_pool': ID oddiy — Random ID hovuziga AVTOMATIK qaytadi
        (boshqa foydalanuvchilar aylantirsa tushishi mumkin bo'ladi)."""
    from treasury import get_fund_balance
    from coins import add_coins
    offer = query_one("SELECT * FROM id_sell_offers WHERE id=?", (offer_id,))
    if not offer or offer["status"] not in ("pending", "countered"):
        return False, "Bu taklif allaqachon yakunlangan yoki mavjud emas."

    current_user_id_row = query_one("SELECT id FROM users WHERE custom_id=?", (offer["custom_id"],))
    if not current_user_id_row or current_user_id_row["id"] != offer["user_id"]:
        execute("UPDATE id_sell_offers SET status='cancelled', updated_at=datetime('now') WHERE id=?", (offer_id,))
        return False, "Foydalanuvchining IDsi bu orada o'zgargan, bitim bekor qilindi."

    # MUHIM (tuzatilgan race condition): treasury.py/chests.py/coins.py'dagi
    # bilan bir xil — jamg'arma balansi avval ALOHIDA SELECT bilan
    # tekshirilib, keyin ALOHIDA UPDATE bilan kamaytirilardi. Endi BITTA
    # atomik UPDATE...WHERE bilan.
    fund_row = query_one(
        "UPDATE treasury_fund SET balance=balance-?, updated_at=datetime('now') "
        "WHERE id=1 AND balance >= ? RETURNING balance",
        (final_price, final_price)
    )
    if not fund_row:
        fund_balance = get_fund_balance()
        return False, f"G'aznada yetarli mablag' yo'q ({fund_balance:,} CODE bor, {final_price:,} kerak)."

    execute("INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('out', ?, ?, ?)",
            (final_price, f"ID sotib olindi: #{offer['custom_id']}", offer["user_id"]))
    add_coins(offer["user_id"], final_price, "id_sold_to_admin", offer_id)

    new_id = generate_unique_id()
    _record_id_change(offer["user_id"], new_id, "id_sotdi")
    execute("UPDATE users SET custom_id=? WHERE id=?", (new_id, offer["user_id"]))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (offer["user_id"], "ID'ingiz sotib olindi! 💰",
             f"#{offer['custom_id']} uchun {final_price:,} CODE hisobingizga tushdi. Yangi IDingiz: #{new_id}",
             "success"))

    if disposition == "marketplace":
        price = marketplace_price if marketplace_price and marketplace_price > 0 else int(final_price * 1.3)
        existing_premium = query_one("SELECT id FROM premium_ids WHERE custom_id=?", (offer["custom_id"],))
        if not existing_premium:
            execute("INSERT INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,'available')",
                    (offer["custom_id"], "user_sold", price))
        disposition_note = f"chiroyli ID sifatida bozorga qo'shildi ({price:,} CODE)"
    else:
        # Oddiy ID — Random hovuziga qaytadi: tarixdagi "released_to_pool"
        # belgisini yoqamiz, shunda is_id_in_anyones_history uni endi
        # to'siq deb hisoblamaydi va u qayta Random'da tushishi mumkin.
        execute("UPDATE user_id_history SET released_to_pool=1 WHERE custom_id=?", (offer["custom_id"],))
        disposition_note = "oddiy ID sifatida Random ID hovuziga qaytarildi"

    execute("UPDATE id_sell_offers SET status='completed', handled_by=?, updated_at=datetime('now') WHERE id=?",
            (admin_id, offer_id))
    return True, f"Sotib olindi: #{offer['custom_id']} — {final_price:,} CODE foydalanuvchiga to'landi, {disposition_note}."


def admin_reject_offer(admin_id: int, offer_id: int, note: str = "") -> tuple[bool, str]:
    offer = query_one("SELECT * FROM id_sell_offers WHERE id=? AND status IN ('pending','countered')", (offer_id,))
    if not offer:
        return False, "Faol taklif topilmadi."
    execute("UPDATE id_sell_offers SET status='rejected', handled_by=?, admin_note=?, updated_at=datetime('now') WHERE id=?",
            (admin_id, note, offer_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (offer["user_id"], "ID sotuvi rad etildi",
             f"#{offer['custom_id']} sotuv taklifingiz admin tomonidan rad etildi.", "info"))
    return True, "Taklif rad etildi."
