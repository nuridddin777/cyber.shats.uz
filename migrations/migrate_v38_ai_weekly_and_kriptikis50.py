"""
SHATS CYBER — MIGRATE v38
================================================================================
Uch talabni amalga oshiradi:

1) AI yordamchi endi HAR XABAR uchun emas, balki HAFTALIK obuna asosida
   ishlaydi (FREE foydalanuvchi uchun 1 CODE / hafta, avtomatik yangilanadi).
   Buning uchun `users` jadvaliga `ai_sub_expires_at` ustuni qo'shiladi.

2) Narxlar: pulik kurs narxi standart 10 000 CODE'dan 1 CODE'ga tushiriladi
   (pricing_settings jadvalida ALLAQACHON mavjud qatorni ham majburan
   yangilaydi — chunki pricing.py'dagi DEFAULTS faqat bazada umuman qator
   bo'lmaganda ishlaydi).

3) Maxsus Topshiriq (KRIPTIKIS) 3 bosqichdan 50 bosqichga kengaytiriladi.
   1-49 bosqichlarni yechish/o'tish HECH QANDAY CODE mukofoti bermaydi —
   faqat keyingi bosqichga o'tkazadi. Faqat 50 (YAKUNIY) bosqichni to'g'ri
   yechganda 10 CODE mukofot beriladi. 2- va 3-bosqichlarning ilgari
   qo'lda yozilgan asl shifrlari saqlab qolinadi (faqat mukofoti 0'ga
   tushiriladi), 4-49 oralig'i esa avtomatik (dasturiy) generatsiya
   qilinadi — har biri HEX/XOR shifri, aniq yechilishi mumkin bo'lgan
   formula bilan (hint_text'da ochiq ko'rsatilgan).
"""
import sqlite3
import os
import hashlib

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

SITE_KEY = "SHATS"  # XOR kaliti — sayt nomidan


def _h(answer: str) -> str:
    return hashlib.sha256(answer.strip().upper().encode()).hexdigest()


def _xor_hex(text: str, key: str) -> str:
    out = []
    for i, ch in enumerate(text):
        out.append(f"{ord(ch) ^ ord(key[i % len(key)]):02x}")
    return "".join(out)


def _build_seed():
    seed = [
        (
            1, "KRIPTIKIS — I bosqich",
            "01001011 01010010 01001001 01010000 01010100 01001001 01001011 01001001 01010011\n"
            "( Bu shifr ataylab TO'LIQ hal qilinmaydigan darajada murakkablashtirilgan — vaqtingizni "
            "behuda sarflamang. Bu bosqich CODE evaziga o'tiladi, javob orqali emas. )",
            "Bu bosqichda javob YO'Q — pastdagi tugma orqali CODE to'lab, 2-bosqichga o'ting.",
            2, None, 0, 1
        ),
        (
            2, "KRIPTIKIS — II bosqich",
            "Shifrlangan javob (HEX, XOR shifri): 607b7767657a6f77706b647e776d6a756c77",
            "Kalit 10 harfdan iborat: platformamiz nomining ikki so'zi, katta harflar bilan, bo'shliqsiz "
            "(masalan: BIRINCHISOZ + IKKINCHISOZ). Javob — 18 xonali raqam. "
            "(Eslatma: bu bosqichni yechish CODE mukofoti bermaydi — faqat 3-bosqichga o'tkazadi.)",
            0, _h("336369655976699655"), 0, 1
        ),
        (
            3, "KRIPTIKIS — III bosqich",
            "Shifr: =I2c4FmFAgABWEQEDEBE",
            "3 qatlam: (1) satrni teskari o'qing, (2) Base64'dan dekodlang, (3) natijani "
            "5 harfli kalit bilan XOR qiling — kalit shu saytning birinchi so'zi, katta harflar bilan. "
            "Javob — bitta so'z + yil (masalan: SOZYIL2026 uslubida, bo'shliqsiz, katta harflar bilan). "
            "(Eslatma: bu bosqichni yechish CODE mukofoti bermaydi — faqat 4-bosqichga o'tkazadi.)",
            0, _h("CYBERELITE2026"), 0, 1
        ),
    ]

    # 4 — 49: avtomatik generatsiya qilingan oraliq bosqichlar. Har biri
    # oddiy, lekin aniq formula bilan hal qilinadigan HEX/XOR shifri.
    # Hech biri CODE bermaydi — faqat keyingi bosqichga o'tkazadi.
    for n in range(4, 50):
        answer = f"KOD{n:03d}CYBERSHATS"
        clue_hex = _xor_hex(answer, SITE_KEY)
        title = f"KRIPTIKIS — {n}-bosqich"
        clue = f"Shifrlangan javob (HEX, XOR shifri): {clue_hex}"
        hint = (
            f"Kalit — platforma nomining birinchi so'zi, katta harflar bilan (5 harf). "
            f"XOR shifrini hal qiling. Javob formulasi doim bir xil: "
            f"'KOD' + bosqich raqami (3 xonali, masalan {n:03d}) + 'CYBERSHATS'. "
            f"(Bu bosqich CODE mukofoti bermaydi.)"
        )
        seed.append((n, title, clue, hint, 0, _h(answer), 0, 1))

    # 50 — YAKUNIY bosqich: ko'p qavatli shifr, faqat shu yerda 10 CODE beriladi.
    final_answer = "KRIPTIKISFINAL2026"
    reversed_b64_xor = _xor_hex(final_answer, "CYBER")[::-1]  # murakkablashtirish uchun teskari HEX
    seed.append((
        50, "KRIPTIKIS — YAKUNIY bosqich (50)",
        f"Yakuniy shifr (teskari HEX, XOR): {reversed_b64_xor}",
        "3 qadam: (1) satrni teskari o'qing (asl HEX holatiga qaytaring), (2) HEX'ni XOR shifridan "
        "oching — kalit 5 harfli, ingliz tilida 'raqamli pul' ma'nosini anglatuvchi so'z, katta harflar bilan "
        "(CYBER). Javob — 'KRIPTIKISFINAL' so'zi + yil, bo'shliqsiz, katta harflar bilan. "
        "Bu YAKUNIY bosqich — to'g'ri yechsangiz 10 CODE mukofot olasiz!",
        0, _h(final_answer), 10, 1
    ))
    return seed


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    # --- 1) AI haftalik obuna ustuni ---
    c.execute("PRAGMA table_info(users)")
    user_cols = [r[1] for r in c.fetchall()]
    if "ai_sub_expires_at" not in user_cols:
        c.execute("ALTER TABLE users ADD COLUMN ai_sub_expires_at TEXT DEFAULT NULL")

    # --- 2) Narxlarni majburan yangilash (bazada allaqachon qator bo'lsa ham) ---
    forced_prices = {
        "paid_course_code_default": "1",
        "ai_weekly_price_code": "1",
    }
    for key, value in forced_prices.items():
        c.execute("SELECT value FROM pricing_settings WHERE key=?", (key,))
        row = c.fetchone()
        if row is None:
            c.execute("INSERT INTO pricing_settings (key, value) VALUES (?,?)", (key, value))
        else:
            c.execute("UPDATE pricing_settings SET value=? WHERE key=?", (value, key))

    # --- 3) KRIPTIKIS — 50 bosqichga kengaytirish ---
    seed = _build_seed()
    for row in seed:
        c.execute("""INSERT INTO special_challenges
            (level, title, clue_text, hint_text, unlock_cost_code, answer_hash, reward_code, is_active)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(level) DO UPDATE SET
                title=excluded.title,
                clue_text=excluded.clue_text,
                hint_text=excluded.hint_text,
                unlock_cost_code=excluded.unlock_cost_code,
                answer_hash=excluded.answer_hash,
                reward_code=excluded.reward_code,
                is_active=excluded.is_active
        """, row)

    conn.commit()
    conn.close()
    print("✅ v38 AI haftalik obuna + Kriptikis 50-bosqich + narxlar muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
