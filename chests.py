# ============================================================
# CYBER SHATS — Sandiqlar (loot box) tizimi
# ============================================================
import random
from db import query_one, query_all, execute

TICKET_PRICES = {
    "tariff": {"1": 1, "10": 8},
    "id": {"1": 3, "10": 27},
    "mystery": {"1": 5, "10": 45},
}

# TARIFLAR SANDIG'I — umumiy ochish soniga qarab bosqichma-bosqich mukofot
TARIFF_MILESTONES = [
    (100, "exclusive_theme", "cars", "🏎️ Garage dizayni (bepul)"),
    (200, "plan", "pro", "PRO tarifi (1 oy)"),
    (300, "plan", "cyber_pro", "CYBER PRO tarifi (1 oy)"),
    (577, "plan", "vip", "VIP tarifi (1 oy)"),
    (699, "plan", "hacker", "MAXSUS tarifi (1 oy)"),
]

# ID SANDIG'I — nechta ochishda taxminan 1 marta chiroyli ID tushishi
# (kamdan-kam — qimmatroq/chiroylroq)
ID_CHEST_TIERS = [
    (50, "oddiy", 1, 30),
    (100, "chiroyli", 31, 60),
    (150, "juda chiroyli", 61, 85),
    (300, "eng chiroyli", 86, 100),
]


def _grant_keys() -> int:
    """Har ochilishda 1-10 ta kalit — omadga qarab, lekin doim 1da qolib
    ketmasin deb og'irlik (weight) beriladi (kattaroq sonlar ozroq
    ehtimolli, lekin 1 ham dominant bo'lmasin)."""
    weights = [22, 20, 16, 13, 10, 8, 6, 3, 1.5, 0.5]  # 1..10 kalit
    return random.choices(range(1, 11), weights=weights, k=1)[0]


def get_user_chest_state(user_id: int) -> dict:
    u = query_one(
        "SELECT chest_tickets_tariff, chest_tickets_id, chest_tickets_mystery, chest_keys, "
        "tariff_chest_opens FROM users WHERE id=?", (user_id,))
    return dict(u) if u else {}


def buy_tickets(user_id: int, chest_type: str, qty: str) -> tuple[bool, str]:
    """qty: '1' yoki '10'. chest_type: 'tariff', 'id' yoki 'mystery'."""
    from coins import spend_coins, refund_coins
    if chest_type not in TICKET_PRICES or qty not in ("1", "10"):
        return False, "Noto'g'ri so'rov."
    price = TICKET_PRICES[chest_type][qty]
    amount = 1 if qty == "1" else 10
    ok, msg = spend_coins(user_id, price, f"chest_tickets_{chest_type}")
    if not ok:
        return False, f"{price} CODE kerak, balansingiz yetarli emas."
    col = {"tariff": "chest_tickets_tariff", "id": "chest_tickets_id",
           "mystery": "chest_tickets_mystery"}[chest_type]
    try:
        execute(f"UPDATE users SET {col} = {col} + ? WHERE id=?", (amount, user_id))
    except Exception as e:
        refund_coins(user_id, price, f"chest_tickets_{chest_type}_failed")
        import logging
        logging.getLogger("cybershats").error(f"buy_tickets xato, CODE qaytarildi: {e}")
        return False, "Texnik xatolik yuz berdi. CODE'ingiz balansingizga qaytarildi, qaytadan urinib ko'ring."
    return True, f"{amount} ta chipta sotib olindi ({price} CODE)."


def open_tariff_chest(user_id: int) -> dict:
    """Tariflar sandig'ini ochadi. Har ochish: 1 chipta sarflanadi,
    1-10 kalit tushadi, va agar umumiy ochish soni bosqich (milestone)ga
    yetsa — o'sha bosqich mukofoti BERILADI (bir martalik).

    MUHIM (tuzatilgan xato): chipta sarflangandan KEYIN keyingi qadamlar
    xato bersa — chipta AVTOMATIK qaytariladi (xuddi CODE xaridlaridagi
    kabi).

    MUHIM (tuzatilgan race condition): avval chipta soni ALOHIDA SELECT
    bilan tekshirilib, keyin ALOHIDA UPDATE bilan kamaytirilardi — ikkita
    deyarli bir vaqtdagi so'rov (2 marta bosish, 2 ta tab) bitta
    chiptadan ikkalasi ham foydalanishi mumkin edi. Endi kamaytirish
    BITTA atomik UPDATE...WHERE chest_tickets_tariff >= 1 bilan."""
    updated = query_one(
        "UPDATE users SET chest_tickets_tariff = chest_tickets_tariff - 1, "
        "tariff_chest_opens = tariff_chest_opens + 1 "
        "WHERE id=? AND chest_tickets_tariff >= 1 "
        "RETURNING tariff_chest_opens",
        (user_id,)
    )
    if not updated:
        return {"ok": False, "error": "Chiptangiz yo'q."}

    try:
        new_opens = updated["tariff_chest_opens"]
        keys = _grant_keys()
        execute("UPDATE users SET chest_keys = chest_keys + ? WHERE id=?", (keys, user_id))

        milestone_reward = None
        for threshold, reward_kind, reward_val, reward_label in TARIFF_MILESTONES:
            if new_opens == threshold:
                milestone_reward = (reward_kind, reward_val, reward_label)
                if reward_kind == "exclusive_theme":
                    execute("UPDATE users SET exclusive_theme=? WHERE id=?", (reward_val, user_id))
                elif reward_kind == "plan":
                    execute("UPDATE users SET plan=?, plan_expires_at=datetime('now','+30 days') WHERE id=?",
                            (reward_val, user_id))
                execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                        (user_id, "Katta yutuq! 🎉", f"{threshold}-marta ochganingiz uchun: {reward_label}", "success"))
                break

        execute("INSERT INTO chest_open_log (user_id, chest_type, reward_type, reward_value, keys_won) VALUES (?,?,?,?,?)",
                (user_id, "tariff", "milestone" if milestone_reward else "keys",
                 milestone_reward[2] if milestone_reward else None, keys))
    except Exception as e:
        execute("UPDATE users SET chest_tickets_tariff = chest_tickets_tariff + 1, "
                "tariff_chest_opens = tariff_chest_opens - 1 WHERE id=?", (user_id,))
        import logging
        logging.getLogger("cybershats").error(f"open_tariff_chest xato, chipta qaytarildi: {e}")
        return {"ok": False, "error": "Texnik xatolik yuz berdi. Chiptangiz qaytarildi, qaytadan urinib ko'ring."}

    return {
        "ok": True, "keys_won": keys, "total_opens": new_opens,
        "milestone_hit": bool(milestone_reward),
        "milestone_label": milestone_reward[2] if milestone_reward else None,
        "next_milestone": next((t for t, *_ in TARIFF_MILESTONES if t > new_opens), None),
    }


def open_id_chest(user_id: int) -> dict:
    """ID sandig'ini ochadi — 1-100 oralig'idagi tasodifiy son bilan
    qaysi chiroylik darajadagi ID tushishini aniqlaydi.

    MUHIM (tuzatilgan race condition): open_tariff_chest() dagi bilan bir
    xil — chipta soni endi atomik UPDATE...WHERE bilan tekshiriladi."""
    from ids import generate_random_id_offer
    updated = query_one(
        "UPDATE users SET chest_tickets_id = chest_tickets_id - 1 "
        "WHERE id=? AND chest_tickets_id >= 1 "
        "RETURNING chest_tickets_id",
        (user_id,)
    )
    if not updated:
        return {"ok": False, "error": "ID chiptangiz yo'q."}

    try:
        keys = _grant_keys()
        execute("UPDATE users SET chest_keys = chest_keys + ? WHERE id=?", (keys, user_id))

        roll = random.randint(1, 100)
        tier_label = "oddiy"
        for _, label, lo, hi in ID_CHEST_TIERS:
            if lo <= roll <= hi:
                tier_label = label
                break

        offer = generate_random_id_offer()
        execute("INSERT INTO chest_open_log (user_id, chest_type, reward_type, reward_value, keys_won) VALUES (?,?,?,?,?)",
                (user_id, "id", tier_label, offer["custom_id"], keys))
        # Foydalanuvchi yutgan ID darhol kolleksiyasiga (tarixga) saqlanadi
        execute("INSERT INTO user_id_history (user_id, custom_id, obtained_via, status) VALUES (?,?,?,'released')",
                (user_id, offer["custom_id"], "chest"))
    except Exception as e:
        execute("UPDATE users SET chest_tickets_id = chest_tickets_id + 1 WHERE id=?", (user_id,))
        import logging
        logging.getLogger("cybershats").error(f"open_id_chest xato, chipta qaytarildi: {e}")
        return {"ok": False, "error": "Texnik xatolik yuz berdi. Chiptangiz qaytarildi, qaytadan urinib ko'ring."}

    return {"ok": True, "keys_won": keys, "id_tier": tier_label,
            "custom_id": offer["custom_id"], "id_price": offer["price"]}


def get_checkmark_shop():
    return query_all("SELECT * FROM checkmark_shop WHERE is_active=1")


def buy_checkmark(user_id: int, badge_key: str, pay_with: str) -> tuple[bool, str]:
    """pay_with: 'code' yoki 'keys'."""
    from coins import spend_coins, refund_coins
    item = query_one("SELECT * FROM checkmark_shop WHERE badge_key=? AND is_active=1", (badge_key,))
    if not item:
        return False, "Bu galichka topilmadi."
    if pay_with == "code":
        ok, msg = spend_coins(user_id, item["price_code"], "checkmark_purchase")
        if not ok:
            return False, f"{item['price_code']} CODE kerak."
        try:
            execute("UPDATE users SET checkmark_badge=? WHERE id=?", (badge_key, user_id))
        except Exception as e:
            refund_coins(user_id, item["price_code"], "checkmark_purchase_failed")
            import logging
            logging.getLogger("cybershats").error(f"buy_checkmark (CODE) xato, qaytarildi: {e}")
            return False, "Texnik xatolik yuz berdi. CODE'ingiz qaytarildi."
        return True, f"«{item['label']}» galichkasi faollashtirildi!"
    elif pay_with == "keys":
        updated = query_one(
            "UPDATE users SET chest_keys = chest_keys - ? WHERE id=? AND chest_keys >= ? "
            "RETURNING chest_keys",
            (item["price_keys"], user_id, item["price_keys"])
        )
        if not updated:
            return False, f"{item['price_keys']} kalit kerak, sizda yetarli emas."
        try:
            execute("UPDATE users SET checkmark_badge=? WHERE id=?", (badge_key, user_id))
        except Exception as e:
            execute("UPDATE users SET chest_keys = chest_keys + ? WHERE id=?", (item["price_keys"], user_id))
            import logging
            logging.getLogger("cybershats").error(f"buy_checkmark (kalit) xato, qaytarildi: {e}")
            return False, "Texnik xatolik yuz berdi. Kalitingiz qaytarildi."
        return True, f"«{item['label']}» galichkasi faollashtirildi!"
    else:
        return False, "Noto'g'ri to'lov turi."


def gift_tickets(sender_id: int, friend_id: int, chest_type: str, qty: int) -> tuple[bool, str]:
    """Do'stga chipta sovg'a qilish — faqat DO'ST bo'lgan foydalanuvchilarga."""
    import friends as friends_mod
    if chest_type not in ("tariff", "id"):
        return False, "Noto'g'ri sandiq turi."
    if qty < 1 or qty > 50:
        return False, "1 dan 50 gacha chipta sovg'a qilish mumkin."
    if friends_mod.get_friendship_status(sender_id, friend_id) != "friends":
        return False, "Faqat do'stlaringizga chipta sovg'a qila olasiz."
    col = "chest_tickets_tariff" if chest_type == "tariff" else "chest_tickets_id"
    updated = query_one(
        f"UPDATE users SET {col} = {col} - ? WHERE id=? AND {col} >= ? RETURNING {col}",
        (qty, sender_id, qty)
    )
    if not updated:
        return False, "Sizda yetarli chipta yo'q."
    execute(f"UPDATE users SET {col} = {col} + ? WHERE id=?", (qty, friend_id))
    sender_name = query_one("SELECT ism, familiya FROM users WHERE id=?", (sender_id,))
    chest_label = "Tarif" if chest_type == "tariff" else "ID"
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (friend_id, "Sovg'a keldi! 🎁",
             f"{sender_name['familiya']} {sender_name['ism']} sizga {qty} ta {chest_label} sandig'i chiptasi sovg'a qildi!",
             "success"))
    return True, f"{qty} ta chipta do'stingizga sovg'a qilindi!"
