"""
CYBER SHATS — To'lov agregatorlari bilan ishlash moduli (Click / Payme / Uzum Pay).

MUHIM: bu modul UZCARD/HUMO/VISA/MASTERCARD'ni to'g'ridan-to'g'ri o'zi
qayta ishlamaydi — karta ma'lumotlari HECH QACHON bizning serverimizga
tushmaydi. Foydalanuvchi agregatorning o'z (litsenziyalangan) checkout
sahifasiga yo'naltiriladi, u yerda kartasini kiritadi, so'ng agregator
bizga natija haqida webhook orqali xabar beradi (payment_webhooks.py).

Ishga tushirish uchun kerak (config.py / .env orqali):
    CLICK_MERCHANT_ID, CLICK_SERVICE_ID, CLICK_SECRET_KEY
    PAYME_MERCHANT_ID, PAYME_SECRET_KEY
    UZUM_MERCHANT_ID, UZUM_SECRET_KEY

Bular hozircha bo'sh ("") — ya'ni tizim SANDBOX/DEMO rejimida ishlaydi:
checkout havolasi yaratiladi, lekin haqiqiy bank orqali o'tmaydi.
Merchant hisobingiz tayyor bo'lgach, faqat .env faylga kalitlarni
qo'yish kifoya — kodni o'zgartirish shart emas.
"""
import hashlib
import secrets
import time
import urllib.parse

from config import Config
from db import query_one, execute, log_action

# ------------------------------------------------------------------
# Qo'llab-quvvatlanadigan provayderlar va ular orqali ishlaydigan kartalar
# ------------------------------------------------------------------
PROVIDERS = {
    "click": {
        "label": "Click",
        "cards": ["uzcard", "humo", "visa", "mastercard"],
        "checkout_base": "https://my.click.uz/services/pay",
    },
    "payme": {
        "label": "Payme",
        "cards": ["uzcard", "humo", "visa", "mastercard"],
        "checkout_base": "https://checkout.paycom.uz",
    },
    "uzum": {
        "label": "Uzum Pay",
        "cards": ["uzcard", "humo", "visa", "mastercard"],
        "checkout_base": "https://checkout.uzumbank.uz",
    },
}


def _provider_configured(provider: str) -> bool:
    """Berilgan provayder uchun haqiqiy merchant kalitlari kiritilganmi tekshiradi."""
    if provider == "click":
        return bool(Config.CLICK_MERCHANT_ID and Config.CLICK_SERVICE_ID and Config.CLICK_SECRET_KEY)
    if provider == "payme":
        return bool(Config.PAYME_MERCHANT_ID and Config.PAYME_SECRET_KEY)
    if provider == "uzum":
        return bool(Config.UZUM_MERCHANT_ID and Config.UZUM_SECRET_KEY)
    return False


def get_available_providers() -> list[dict]:
    """Foydalanuvchiga ko'rsatiladigan to'lov usullari ro'yxati (holati bilan)."""
    result = []
    for key, meta in PROVIDERS.items():
        result.append({
            "key": key,
            "label": meta["label"],
            "cards": meta["cards"],
            "configured": _provider_configured(key),
        })
    return result


def _new_merchant_trans_id() -> str:
    """Bizning tomonimizda generatsiya qilinadigan unikal buyurtma ID (idempotentlik uchun)."""
    return f"SHATS-{int(time.time())}-{secrets.token_hex(4)}"


def create_payment_order(user_id: int, amount_uzs: int, code_amount: int,
                          provider: str, card_type: str = "") -> tuple[bool, str, dict]:
    """
    Yangi to'lov buyurtmasi yaratadi va foydalanuvchini yo'naltirish uchun
    checkout URL qaytaradi. Haqiqiy pul hali yechilmagan — bu faqat
    "to'lovga tayyorlash" bosqichi. Yakuniy tasdiq — webhook orqali keladi.
    """
    if provider not in PROVIDERS:
        return False, "Noma'lum to'lov usuli.", {}
    if amount_uzs <= 0:
        return False, "Summani to'g'ri kiriting.", {}

    merchant_trans_id = _new_merchant_trans_id()

    execute(
        """INSERT INTO payment_transactions
           (user_id, provider, merchant_trans_id, card_type, amount_uzs, code_amount, status)
           VALUES (?,?,?,?,?,?, 'pending')""",
        (user_id, provider, merchant_trans_id, card_type, amount_uzs, code_amount)
    )
    log_action(user_id, "payment_order_created",
               details=f"provider:{provider},amount:{amount_uzs},code:{code_amount},trans:{merchant_trans_id}")

    if not _provider_configured(provider):
        # SANDBOX rejim: haqiqiy merchant kaliti yo'q — demo checkout sahifasiga yo'naltiramiz.
        checkout_url = f"/payment/sandbox-checkout/{merchant_trans_id}"
        return True, "Sandbox rejim: haqiqiy merchant kaliti kiritilmagan.", {
            "checkout_url": checkout_url,
            "merchant_trans_id": merchant_trans_id,
            "sandbox": True,
        }

    checkout_url = _build_checkout_url(provider, merchant_trans_id, amount_uzs)
    return True, "Buyurtma yaratildi.", {
        "checkout_url": checkout_url,
        "merchant_trans_id": merchant_trans_id,
        "sandbox": False,
    }


def _build_checkout_url(provider: str, merchant_trans_id: str, amount_uzs: int) -> str:
    """Har bir agregatorning o'z checkout URL formatiga mos havola quradi."""
    return_url = f"{Config.SITE_PUBLIC_URL}/payment/return/{merchant_trans_id}"

    if provider == "click":
        # Click "Checkout" (invoice) usuli — rasmiy hujjat: https://docs.click.uz
        params = {
            "service_id": Config.CLICK_SERVICE_ID,
            "merchant_id": Config.CLICK_MERCHANT_ID,
            "amount": amount_uzs,
            "transaction_param": merchant_trans_id,
            "return_url": return_url,
        }
        return PROVIDERS["click"]["checkout_base"] + "?" + urllib.parse.urlencode(params)

    if provider == "payme":
        # Payme Checkout — parametrlar base64 qilib /{base64} shaklida beriladi
        import base64
        raw = (
            f"m={Config.PAYME_MERCHANT_ID};"
            f"ac.order_id={merchant_trans_id};"
            f"a={amount_uzs * 100};"          # Payme summani tiyinda kutadi
            f"c={return_url}"
        )
        token = base64.b64encode(raw.encode()).decode()
        return f"{PROVIDERS['payme']['checkout_base']}/{token}"

    if provider == "uzum":
        params = {
            "merchant_id": Config.UZUM_MERCHANT_ID,
            "order_id": merchant_trans_id,
            "amount": amount_uzs,
            "return_url": return_url,
        }
        return PROVIDERS["uzum"]["checkout_base"] + "?" + urllib.parse.urlencode(params)

    return "/coins/buy"


def get_transaction(merchant_trans_id: str):
    return query_one("SELECT * FROM payment_transactions WHERE merchant_trans_id=?", (merchant_trans_id,))


def mark_paid(merchant_trans_id: str, provider_txn_id: str, raw_payload: str = "") -> bool:
    """To'lov muvaffaqiyatli deb belgilaydi va CODE'ni AVTOMATIK foydalanuvchiga o'tkazadi.

    Idempotent: bir xil tranzaksiya ikki marta CODE bermaydi. MUHIM
    (tuzatilgan race condition): avval ALOHIDA SELECT bilan status
    tekshirilib, keyin ALOHIDA UPDATE bilan 'paid'ga o'tkazilardi — bank
    agregatorlari (Click/Payme/Uzum) webhookni ba'zan qayta yuboradi
    (retry), va ikkita chaqiruv deyarli bir vaqtda kelsa, ikkalasi ham
    HALI 'paid' bo'lmagan holatni o'qib, ikkalasi ham CODE qo'shishi
    mumkin edi. Endi status='paid'ga o'tish BITTA atomik UPDATE...WHERE
    status != 'paid' bilan amalga oshiriladi — faqat shu UPDATE
    haqiqatan bitta qatorni o'zgartirgan chaqiruvgina CODE qo'shadi."""
    txn = get_transaction(merchant_trans_id)
    if not txn:
        return False

    updated = query_one(
        """UPDATE payment_transactions
           SET status='paid', provider_txn_id=?, paid_at=datetime('now'), raw_payload=?
           WHERE merchant_trans_id=? AND status != 'paid'
           RETURNING merchant_trans_id""",
        (provider_txn_id, raw_payload, merchant_trans_id)
    )
    if not updated:
        return True  # allaqachon qayta ishlangan — qayta CODE bermaymiz

    # --- AVTOMATIK CODE SOLISH ---
    execute("UPDATE users SET code_balance = code_balance + ? WHERE id=?",
            (txn["code_amount"], txn["user_id"]))
    execute(
        "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
        (txn["user_id"], "To'lov qabul qilindi!",
         f"{txn['amount_uzs']:,} so'm to'lovingiz tasdiqlandi. "
         f"Hisobingizga avtomatik {txn['code_amount']:,} CODE qo'shildi.", "success")
    )
    log_action(txn["user_id"], "payment_auto_credited",
               details=f"trans:{merchant_trans_id},code:{txn['code_amount']}")
    return True


def mark_failed(merchant_trans_id: str, reason: str = "") -> bool:
    txn = get_transaction(merchant_trans_id)
    if not txn or txn["status"] == "paid":
        return False
    execute("UPDATE payment_transactions SET status='failed', raw_payload=? WHERE merchant_trans_id=?",
            (reason, merchant_trans_id))
    return True
