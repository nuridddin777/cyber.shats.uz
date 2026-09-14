"""
CYBER SHATS V1.3 — Saytdan to'g'ridan-to'g'ri CODE sotib olish moduli.

Foydalanuvchi o'z panelidan:
1. ID kiritadi (yoki o'z ID'si avtomatik)
2. CODE miqdorini tanlaydi yoki o'zi yozadi (1 CODE = 1 so'm)
3. Karta raqamlari ko'rsatiladi
4. To'lov chekini rasm/fayl sifatida yuklaydi
5. G'azna (botdagi kabi) tekshirib tasdiqlaydi yoki rad etadi
6. Tasdiqlansa — CODE jamg'armadan foydalanuvchiga o'tadi
"""
from db import query_one, query_all, execute, log_action
from pricing import get_price
from utils import resolve_user_id
import datetime

PAYMENT_CARDS = {
    "uzum_bank": "4916 9903 5863 3797",
}
CARD_HOLDER = "Q.TEMUROV"

_DEFAULT_PACKAGES = [1, 5, 10, 15, 20, 25, 30]

MIN_AMOUNT = 1
MAX_AMOUNT = 100_000_000


def get_packages_with_prices() -> list[dict]:
    """Bazadan paket narxlarini qaytaradi."""
    try:
        rows = query_all("SELECT key, value FROM pricing_settings WHERE key LIKE 'code_pack_%' ORDER BY CAST(REPLACE(key,'code_pack_','') AS INTEGER)")
        if rows:
            return [{"amount": int(r["key"].replace("code_pack_","")), "price": int(r["value"])} for r in rows]
    except Exception:
        pass
    rate = get_price("code_to_som_rate") or 10_000
    return [{"amount": a, "price": a * rate} for a in _DEFAULT_PACKAGES]


def get_suggested_packages() -> list[int]:
    pkgs = get_packages_with_prices()
    return [p["amount"] for p in pkgs]


# Eski mos kelish uchun
SUGGESTED_PACKAGES = _DEFAULT_PACKAGES


def redeem_promo_code(code: str, user_id: int) -> tuple[bool, str]:
    """Promo kodni faollashtiradi — HECH QANDAY XARID SHART EMAS, kod to'g'ri
    bo'lsa CODE bonusi bevosita balansga qo'shiladi. DIQQAT: avval promo
    kodlar CODE sotib olish narxidan % yoki qat'iy CHEGIRMA berardi — endi
    bu tamoman olib tashlandi, promo kod = mustaqil CODE bonusi."""
    from coins import add_coins
    if not code or not code.strip():
        return False, "Promo kod kiritilmagan."
    code = code.strip().upper()
    promo = query_one("SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code,))
    if not promo:
        return False, "Promo kod topilmadi yoki faol emas."

    if promo["expires_at"]:
        try:
            exp = datetime.datetime.fromisoformat(promo["expires_at"])
            if datetime.datetime.now() > exp:
                return False, "Promo kodning muddati tugagan."
        except Exception:
            pass

    if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
        return False, "Promo kod foydalanish limiti tugagan."

    already = query_one("SELECT id FROM promo_code_uses WHERE promo_id=? AND user_id=?", (promo["id"], user_id))
    if already:
        return False, "Siz bu promo kodni allaqachon ishlatgansiz."

    bonus = promo["bonus_code_amount"] or 0
    if bonus <= 0:
        return False, "Bu promo kodda bonus miqdori sozlanmagan."

    add_coins(user_id, bonus, "promo_code_bonus", promo["id"])
    execute("INSERT INTO promo_code_uses (promo_id, user_id) VALUES (?,?)", (promo["id"], user_id))
    execute("UPDATE promo_codes SET used_count=used_count+1 WHERE id=?", (promo["id"],))
    return True, f"Promo kod faollashtirildi! +{bonus:,} CODE balansingizga qo'shildi."


def create_site_purchase_request(user_id: int, custom_id: str, amount: int,
                                  receipt_file_path: str, discount: int = 0,
                                  promo_code: str = None) -> tuple[bool, str, int]:
    """Foydalanuvchi saytdan CODE sotib olish so'rovini yaratadi (g'azna tasdiqlashi kerak)."""
    if amount < MIN_AMOUNT:
        return False, f"Minimal miqdor: {MIN_AMOUNT:,} CODE.", 0
    if amount > MAX_AMOUNT:
        return False, "Miqdor juda katta.", 0
    if not receipt_file_path:
        return False, "Chek rasmi/fayli majburiy.", 0

    recipient_id = resolve_user_id(custom_id)
    if not recipient_id:
        return False, "Bu ID saytda topilmadi.", 0

    # Paket narxini bazadan olish
    packages = get_packages_with_prices()
    price_uzs = amount  # standart 1:1
    for p in packages:
        if p["amount"] == amount:
            price_uzs = p["price"]
            break

    # Promo chegirma
    final_price = max(0, price_uzs - discount)

    rid = execute(
        """INSERT INTO bot_purchase_requests
           (request_type, code_amount, price_uzs, target_custom_id, site_user_id,
            receipt_file_path, source, status)
           VALUES ('code', ?, ?, ?, ?, ?, 'site', 'pending')""",
        (amount, final_price, custom_id, recipient_id, receipt_file_path)
    )
    log_action(user_id, "site_code_purchase_request",
               details=f"amount:{amount},price:{final_price},promo:{promo_code},req:{rid}")

    msg = f"So'rov yuborildi! G'azna tekshirib, tez orada tasdiqlaydi."
    if discount > 0:
        msg += f" Promo chegirma: {discount:,} so'm qo'llanildi."
    return True, msg, rid


def get_user_purchase_requests(user_id: int, limit: int = 20):
    return query_all(
        """SELECT * FROM bot_purchase_requests
           WHERE site_user_id=? AND source='site'
           ORDER BY id DESC LIMIT ?""",
        (user_id, limit)
    )
