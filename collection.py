# ============================================================
# CYBER SHATS — Koleksiya (106 haykalcha) tizimi
# ============================================================
import random
import math
import os
from db import query_one, query_all, execute

TOTAL_LEVELS = 106  # 100 (5 toifa) + 5 (bonus, kamalak) + 1 (yakuniy, CYBER SHATS)
MAX_PINNED = 10
STATUETTE_IMG_DIR = os.path.join(os.path.dirname(__file__), "static", "img", "statuettes")


def has_real_image(level: int) -> bool:
    """Agar shu daraja uchun HAQIQIY rasm (static/img/statuettes/{level}.webp)
    yuklangan bo'lsa True — shunda SVG o'rniga o'sha rasm ko'rsatiladi.
    Rasm hali yuklanmagan darajalar avtomatik ravishda SVG generatorga
    tushib qoladi — sayt hech qachon buzilmaydi, bosqichma-bosqich rasm
    qo'shib borish mumkin."""
    return os.path.exists(os.path.join(STATUETTE_IMG_DIR, f"{level}.webp"))

# Tier 1 (81-100) statuettalarini CODE bilan sotib olish narxi — 15 dan 25
# CODEgacha, daraja oshgani sari qimmatlashadi.
def tier1_price(level: int) -> int:
    # 81 -> 15 CODE, 100 -> 25 CODE, oralig'i chiziqli
    return round(15 + (level - 81) / 19 * 10)


def get_tier(level: int) -> dict:
    """Daraja qaysi toifaga (fon rangiga) tegishli ekanini qaytaradi."""
    if level <= 20:
        return {"tier": 5, "bg": "#0F2A5C", "bg2": "#0A1D40", "label": "5-toifa", "source": "Maxsus sandig'i"}
    elif level <= 40:
        return {"tier": 4, "bg": "#1E7A3C", "bg2": "#145229", "label": "4-toifa", "source": "Maxsus sandig'i"}
    elif level <= 60:
        return {"tier": 3, "bg": "#6A2FA0", "bg2": "#4A1F70", "label": "3-toifa", "source": "Maxsus sandig'i"}
    elif level <= 80:
        return {"tier": 2, "bg": "#B01E2E", "bg2": "#7A1420", "label": "2-toifa", "source": "Maxsus sandig'i"}
    elif level <= 100:
        return {"tier": 1, "bg": "#B8860B", "bg2": "#8A6608", "label": "1-toifa (Tilla)", "source": f"CODE (⚡{tier1_price(level)})"}
    elif level <= 105:
        return {"tier": 0, "bg": "rainbow", "bg2": "rainbow", "label": "Bonus (Kamalak)", "source": "Kalitlar (achko)"}
    else:  # 106
        return {"tier": -1, "bg": "multicolor", "bg2": "multicolor", "label": "CYBER SHATS — Yakuniy",
                "source": "Barcha 105 tasi yig'ilgach avtomatik"}


def _statuette_fill(level: int, tier: dict) -> str:
    if level == TOTAL_LEVELS:
        return "MULTI"  # yakuniy — maxsus ko'p rangli chizish
    if tier["tier"] == 0:
        return "#F0F0F5"  # bonus — kumush-oq
    return "#E8E8EE"  # oddiy haykalchalar — metall-kumush (fon ranggi toifani bildiradi)


def generate_statuette_svg(level: int, size: int = 120) -> str:
    """Har bir daraja uchun MUSTAQIL, prosedural (daraja raqami "urug'"
    sifatida) shaklda haykalcha SVG'si — hech ikkitasi bir xil emas.
    106-daraja (CYBER SHATS, yakuniy) — mutlaqo boshqacha, ko'p rangli
    maxsus dizayn."""
    tier = get_tier(level)

    if level == TOTAL_LEVELS:
        # YAKUNIY HAYKALCHA — har xil ranglardan foydalanilgan, mutlaqo
        # boshqacha shakl (yulduz-gemma kombinatsiyasi, ko'p rangli).
        return f'''<svg viewBox="0 0 120 120" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <radialGradient id="finalbg" cx="50%" cy="35%" r="75%">
    <stop offset="0%" stop-color="#1a1a1a"/><stop offset="100%" stop-color="#000000"/>
  </radialGradient>
  <linearGradient id="finalstar" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="#ff3b3b"/><stop offset="25%" stop-color="#ffb238"/>
    <stop offset="50%" stop-color="#3bff8a"/><stop offset="75%" stop-color="#3b82ff"/>
    <stop offset="100%" stop-color="#c23bff"/>
  </linearGradient>
</defs>
<circle cx="60" cy="60" r="58" fill="url(#finalbg)"/>
<ellipse cx="60" cy="100" rx="28" ry="6" fill="rgba(212,175,55,.25)"/>
<polygon points="60,14 71,45 104,45 77,64 88,96 60,76 32,96 43,64 16,45 49,45"
  fill="url(#finalstar)" stroke="#D4AF37" stroke-width="2.5"/>
<circle cx="60" cy="60" r="9" fill="#D4AF37" stroke="#fff" stroke-width="1.5"/>
</svg>'''

    rnd = random.Random(level * 7919 + 13)
    fill = _statuette_fill(level, tier)

    cx, cy = 60, 60
    head_r = 10 + rnd.randint(0, 6)
    body_w = 20 + rnd.randint(0, 14)
    body_h = 28 + rnd.randint(0, 10)
    sides = rnd.choice([3, 4, 5, 6, 8])
    rotation = rnd.randint(0, 359)
    facet_count = rnd.randint(2, 5)

    body_pts = []
    for i in range(sides):
        ang = 2 * math.pi * i / sides + math.radians(rotation)
        px = cx + (body_w / 2) * math.cos(ang)
        py = (cy + 14) + (body_h / 2) * math.sin(ang)
        body_pts.append(f"{px:.1f},{py:.1f}")
    body_poly = " ".join(body_pts)

    facets = ""
    for i in range(facet_count):
        ang = 2 * math.pi * i / facet_count + math.radians(rotation)
        x2 = cx + (body_w / 2.6) * math.cos(ang)
        y2 = (cy + 14) + (body_h / 2.6) * math.sin(ang)
        facets += f'<line x1="{cx}" y1="{cy+14}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(0,0,0,.15)" stroke-width="1"/>'

    if tier["bg"] == "rainbow":
        bg_style = (f'<defs><linearGradient id="rbg{level}" x1="0" y1="0" x2="1" y2="1">'
                    f'<stop offset="0%" stop-color="#ff3b3b"/><stop offset="20%" stop-color="#ffb238"/>'
                    f'<stop offset="40%" stop-color="#ffe93b"/><stop offset="60%" stop-color="#3bff6a"/>'
                    f'<stop offset="80%" stop-color="#3b82ff"/><stop offset="100%" stop-color="#a83bff"/>'
                    f'</linearGradient></defs>')
        bg_fill = f"url(#rbg{level})"
    else:
        bg_style = (f'<defs><radialGradient id="bg{level}" cx="50%" cy="35%" r="75%">'
                    f'<stop offset="0%" stop-color="{tier["bg"]}"/><stop offset="100%" stop-color="{tier["bg2"]}"/>'
                    f'</radialGradient></defs>')
        bg_fill = f"url(#bg{level})"

    return f'''<svg viewBox="0 0 120 120" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
{bg_style}
<circle cx="60" cy="60" r="58" fill="{bg_fill}"/>
<ellipse cx="60" cy="98" rx="26" ry="6" fill="rgba(0,0,0,.25)"/>
<polygon points="{body_poly}" fill="{fill}" stroke="rgba(0,0,0,.2)" stroke-width="1.5"/>
{facets}
<circle cx="{cx}" cy="{cy-10}" r="{head_r}" fill="{fill}" stroke="rgba(0,0,0,.2)" stroke-width="1.5"/>
<circle cx="{cx-head_r*0.3:.1f}" cy="{cy-10-head_r*0.3:.1f}" r="{head_r*0.35:.1f}" fill="rgba(255,255,255,.5)"/>
</svg>'''


def get_user_collection(user_id: int) -> list[dict]:
    unlocked = {r["level"] for r in query_all("SELECT level FROM user_collection WHERE user_id=?", (user_id,))}
    result = []
    for lvl in range(1, TOTAL_LEVELS + 1):
        tier = get_tier(lvl)
        result.append({
            "level": lvl, "tier": tier, "unlocked": lvl in unlocked,
            "is_final": lvl == TOTAL_LEVELS,
            "has_image": has_real_image(lvl),
        })
    return result


def _grant_level(user_id: int, level: int, notify: bool = True):
    already = query_one("SELECT id FROM user_collection WHERE user_id=? AND level=?", (user_id, level))
    if already:
        return False  # takror — allaqachon bor
    execute("INSERT INTO user_collection (user_id, level) VALUES (?,?)", (user_id, level))
    if notify:
        tier = get_tier(level)
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user_id, "Yangi haykalcha! 🏆", f"{level}-daraja ({tier['label']}) koleksiyangizga qo'shildi.", "success"))
    _check_final_statuette(user_id)
    return True


def _check_final_statuette(user_id: int):
    """106-daraja (CYBER SHATS) — FAQAT barcha 105 tasi yig'ilgandan
    so'ng avtomatik beriladi, boshqa hech qanday yo'l bilan olinmaydi."""
    if query_one("SELECT id FROM user_collection WHERE user_id=? AND level=?", (user_id, TOTAL_LEVELS)):
        return
    count = query_one("SELECT COUNT(*) c FROM user_collection WHERE user_id=? AND level < ?",
                      (user_id, TOTAL_LEVELS))["c"]
    if count >= TOTAL_LEVELS - 1:
        execute("INSERT INTO user_collection (user_id, level) VALUES (?,?)", (user_id, TOTAL_LEVELS))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user_id, "🌟 YAKUNIY HAYKALCHA! 🌟",
                 "Barcha 105 ta haykalchani yig'dingiz! Noyob «CYBER SHATS» haykalchasi sizga berildi.", "success"))


# ---- Toifa 5-4-3-2 (1-80 daraja) — FAQAT Maxsus sandig'idan (Box 3) ----
# Og'irlik pastroq toifa (5) ko'proq, yuqoriroq toifa (2) kamroq tushadi.
MYSTERY_TIER_WEIGHTS = [(5, 45), (4, 28), (3, 17), (2, 10)]


def open_mystery_chest(user_id: int) -> dict:
    from chests import _grant_keys
    # MUHIM (tuzatilgan race condition): chests.py'dagi bilan bir xil —
    # chipta soni endi atomik UPDATE...WHERE bilan tekshiriladi.
    updated = query_one(
        "UPDATE users SET chest_tickets_mystery = chest_tickets_mystery - 1 "
        "WHERE id=? AND chest_tickets_mystery >= 1 "
        "RETURNING chest_tickets_mystery",
        (user_id,)
    )
    if not updated:
        return {"ok": False, "error": "Maxsus sandiq chiptangiz yo'q."}

    try:
        tiers, weights = zip(*MYSTERY_TIER_WEIGHTS)
        chosen_tier = random.choices(tiers, weights=weights, k=1)[0]
        tier_ranges = {5: (1, 20), 4: (21, 40), 3: (41, 60), 2: (61, 80)}
        lo, hi = tier_ranges[chosen_tier]
        level = random.randint(lo, hi)

        is_new = _grant_level(user_id, level, notify=False)
        keys = _grant_keys()
        execute("UPDATE users SET chest_keys = chest_keys + ? WHERE id=?", (keys, user_id))
        execute("INSERT INTO chest_open_log (user_id, chest_type, reward_type, reward_value, keys_won) VALUES (?,?,?,?,?)",
                (user_id, "mystery", "statuette", str(level), keys))
    except Exception as e:
        execute("UPDATE users SET chest_tickets_mystery = chest_tickets_mystery + 1 WHERE id=?", (user_id,))
        import logging
        logging.getLogger("cybershats").error(f"open_mystery_chest xato, chipta qaytarildi: {e}")
        return {"ok": False, "error": "Texnik xatolik yuz berdi. Chiptangiz qaytarildi, qaytadan urinib ko'ring."}

    return {"ok": True, "level": level, "tier": get_tier(level), "is_new": is_new, "keys_won": keys}


def buy_tier1_statuette(user_id: int, level: int) -> tuple[bool, str]:
    """1-toifa (81-100 daraja) haykalchalarini to'g'ridan-to'g'ri CODEga sotib olish."""
    from coins import spend_coins, refund_coins
    if not (81 <= level <= 100):
        return False, "Bu daraja CODE bilan sotib olinmaydi."
    if query_one("SELECT id FROM user_collection WHERE user_id=? AND level=?", (user_id, level)):
        return False, "Bu haykalcha sizda allaqachon bor."
    price = tier1_price(level)
    ok, msg = spend_coins(user_id, price, "statuette_purchase")
    if not ok:
        return False, f"{price} CODE kerak, balansingiz yetarli emas."
    try:
        _grant_level(user_id, level, notify=False)
    except Exception as e:
        refund_coins(user_id, price, "statuette_purchase_failed")
        import logging
        logging.getLogger("cybershats").error(f"buy_tier1_statuette xato, CODE qaytarildi: {e}")
        return False, "Texnik xatolik yuz berdi. CODE'ingiz balansingizga qaytarildi, qaytadan urinib ko'ring."
    return True, f"{level}-daraja haykalchasi sotib olindi ({price} CODE)!"


# ---- Kalitlar (achko) orqali — bonus toifa (101-105) va TAKRORIY tushish ----
KEY_REDEEM_COST = 50


def redeem_keys_for_statuette(user_id: int) -> dict:
    """Kalitlarni sarflab, tasodifiy haykalcha uchun IMKONIYAT beradi —
    HAR SAFAR EMAS (bo'sh chiqishi ham mumkin), va allaqachon bor
    haykalcha ham TAKROR tushishi mumkin (faqat bildirishnoma/tarix
    uchun — koleksiyaga qo'shimcha o'zgartirish kiritmaydi)."""
    # MUHIM (tuzatilgan race condition): chests.py'dagi bilan bir xil —
    # kalit soni endi atomik UPDATE...WHERE bilan tekshiriladi.
    updated = query_one(
        "UPDATE users SET chest_keys = chest_keys - ? WHERE id=? AND chest_keys >= ? "
        "RETURNING chest_keys",
        (KEY_REDEEM_COST, user_id, KEY_REDEEM_COST)
    )
    if not updated:
        return {"ok": False, "error": f"{KEY_REDEEM_COST} kalit kerak."}

    # 55% — hech narsa (omadsiz), 30% — oddiy toifadan (1-100 ichidan tasodifiy,
    # takror bo'lishi mumkin), 15% — bonus toifadan (101-105)
    roll = random.random()
    if roll < 0.55:
        execute("INSERT INTO chest_open_log (user_id, chest_type, reward_type, reward_value, keys_won) VALUES (?,?,?,?,?)",
                (user_id, "key_redeem", "empty", None, 0))
        return {"ok": True, "won": False}
    elif roll < 0.85:
        level = random.randint(1, 100)
    else:
        level = random.randint(101, 105)

    is_new = _grant_level(user_id, level, notify=False)
    execute("INSERT INTO chest_open_log (user_id, chest_type, reward_type, reward_value, keys_won) VALUES (?,?,?,?,?)",
            (user_id, "key_redeem", "statuette", str(level), 0))
    return {"ok": True, "won": True, "level": level, "tier": get_tier(level), "is_new": is_new}


def pin_statuette(user_id: int, level: int) -> tuple[bool, str]:
    owned = query_one("SELECT id FROM user_collection WHERE user_id=? AND level=?", (user_id, level))
    if not owned:
        return False, "Bu haykalcha hali ochilmagan."
    count = query_one("SELECT COUNT(*) c FROM user_pinned_statuettes WHERE user_id=?", (user_id,))["c"]
    if count >= MAX_PINNED:
        return False, f"Ko'pi bilan {MAX_PINNED} ta haykalcha ko'rgazmaga qo'yish mumkin."
    existing = query_one("SELECT id FROM user_pinned_statuettes WHERE user_id=? AND level=?", (user_id, level))
    if existing:
        return False, "Bu haykalcha allaqachon ko'rgazmada."
    execute("INSERT INTO user_pinned_statuettes (user_id, level, pin_order) VALUES (?,?,?)",
            (user_id, level, count))
    return True, "Haykalcha profilingizga qo'yildi."


def unpin_statuette(user_id: int, level: int) -> tuple[bool, str]:
    execute("DELETE FROM user_pinned_statuettes WHERE user_id=? AND level=?", (user_id, level))
    return True, "Haykalcha ko'rgazmadan olindi."


def get_pinned_statuettes(user_id: int) -> list[dict]:
    rows = query_all("SELECT level FROM user_pinned_statuettes WHERE user_id=? ORDER BY pin_order", (user_id,))
    return [{"level": r["level"], "tier": get_tier(r["level"])} for r in rows]
