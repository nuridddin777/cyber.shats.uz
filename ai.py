# ============================================================
# CYBER SHATS — AI Yordamchi backend logikasi
#
# Ikkita haqiqiy AI provayder qo'llab-quvvatlanadi:
#   1) GOOGLE GEMINI (.env -> GEMINI_API_KEY) — TEKIN tarif (kredit karta
#      shart emas), lekin daqiqa/kunlik so'rov cheklovi bor. Ustuvor
#      tanlov — agar sozlangan bo'lsa, birinchi shu ishlatiladi.
#   2) ANTHROPIC CLAUDE (.env -> ANTHROPIC_API_KEY) — pullik, lekin
#      Gemini sozlanmagan/xato bergan holatda zaxira sifatida ishlatiladi.
#
# Ikkalasi ham sozlanmagan bo'lsa — tayyor (canned) demo javob qaytariladi,
# interfeys baribir to'liq ishlaydi, faqat javoblar statik bo'ladi.
# ============================================================
import os
import base64
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.0-flash-preview-image-generation").strip()
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

ASSISTANT_PROMPTS = {
    "umumiy": "Sen CYBER SHATS platformasining umumiy AI yordamchisisan. IT va dasturlash bo'yicha savollarga "
              "o'zbek tilida, qisqa va aniq javob ber.",
    "kod": "Sen tajribali dasturchisan. Foydalanuvchiga kod yozishda, xatolarni topishda va tushuntirishda "
           "yordam ber. Javoblarni o'zbek tilida ber, kod bloklarini saqlab qoldir.",
    "cyber": "Sen kiberxavfsizlik bo'yicha mutaxassissan (ethical hacking, pentest, tarmoq xavfsizligi). "
             "Faqat ta'lim maqsadida, qonuniy va axloqiy doirada maslahat ber. O'zbek tilida javob ber.",
    "design": "Sen UI/UX va veb-dizayn bo'yicha maslahatchisan. O'zbek tilida amaliy tavsiyalar ber.",
    "cloud": "Sen cloud computing (AWS, Docker, Kubernetes, DevOps) bo'yicha mutaxassissan. O'zbek tilida javob ber.",
    "tarix": "Sen IT va kompyuter texnologiyalari tarixi bo'yicha bilimdonsan. Qiziqarli va aniq faktlar bilan "
             "o'zbek tilida javob ber.",
}

FALLBACK_REPLIES = {
    "umumiy": "Salom! Men CYBER SHATS AI yordamchisiman. Hozircha demo rejimida ishlayapman — to'liq javob "
              "olish uchun platforma administratori GEMINI_API_KEY (tekin) yoki ANTHROPIC_API_KEY sozlamasini "
              ".env faylga qo'shishi kerak. Savolingizni saqlab qoldim, key qo'shilgandan so'ng to'liq javob bera olaman.",
    "kod": "Bu demo javob: real kod tahlili uchun .env faylga GEMINI_API_KEY (tekin) yoki ANTHROPIC_API_KEY "
           "qo'shilishi kerak. Hozircha namuna: `for i in range(10): print(i)` — Python'da 0 dan 9 gacha sonlarni chop etadi.",
    "cyber": "Demo rejim: kiberxavfsizlik bo'yicha to'liq AI tahlili uchun API kalit kerak. Eslatma: barcha "
             "pentest amaliyotlari faqat o'ziga tegishli yoki ruxsat berilgan tizimlarda qonuniy qilinishi kerak.",
    "design": "Demo rejim: to'liq dizayn maslahati uchun API kalit kerak. Umumiy maslahat: interfeysni sodda, "
              "izchil va foydalanuvchi uchun tushunarli qilib loyihalashtiring.",
    "cloud": "Demo rejim: to'liq javob uchun API kalit kerak. Umumiy maslahat: ishlab chiqishni boshlashdan "
             "oldin arxitekturani diagram orqali rejalashtiring.",
    "tarix": "Demo rejim: IT tarixi bo'yicha to'liq javob uchun API kalit kerak. Qiziqarli fakt: birinchi "
             "kompyuter virusi 'Creeper' 1971-yilda yaratilgan.",
}


def is_gemini_configured():
    return bool(GEMINI_API_KEY)


def _error_message(e) -> str:
    """Foydalanuvchiga ko'rsatiladigan xato xabari.
    DIQQAT: avval bu yerda XATO bor edi — agar RuntimeError'da matn bo'lsa,
    uni O'ZGARISHSIZ (hatto Gemini serverining xom JSON javobi bo'lsa ham!)
    to'g'ridan-to'g'ri foydalanuvchiga ko'rsatardi — masalan
    '{"error": {"code": 503, "message": "..."}}' kabi texnik matn chiqib
    ketardi. Endi bunday holatlarda ODDIY, tushunarli o'zbekcha xabar
    beriladi."""
    detail = str(e).strip()
    if isinstance(e, RuntimeError) and detail:
        if "503" in detail or "UNAVAILABLE" in detail or "high demand" in detail.lower():
            return ("AI xizmati hozir juda band (server tomonidan vaqtinchalik cheklov). "
                     "Bir necha soniyadan so'ng qayta urinib ko'ring — bu odatda tez tuzatiladi.")
        if "429" in detail:
            return "AI kunlik bepul limitiga yetdik. Birozdan so'ng qayta urinib ko'ring."
        if detail.startswith("{") or "Gemini serverida" in detail:
            return "AI xizmatida vaqtinchalik texnik nosozlik. Birozdan so'ng qayta urinib ko'ring."
        return detail
    import requests as _requests
    if isinstance(e, _requests.exceptions.Timeout):
        return "AI xizmati javob berishga vaqt yetarli bo'lmadi (timeout). Birozdan so'ng qayta urinib ko'ring."
    if isinstance(e, _requests.exceptions.ConnectionError):
        return "AI xizmatiga tarmoq orqali ulanib bo'lmadi. Internet aloqasini tekshiring va qayta urinib ko'ring."
    return (f"AI xizmatiga ulanishda xatolik yuz berdi ({type(e).__name__}: {detail[:150]}). "
            f"Birozdan so'ng qayta urinib ko'ring.")


def is_anthropic_configured():
    return bool(ANTHROPIC_API_KEY)


def is_ai_configured():
    return is_gemini_configured() or is_anthropic_configured()


def active_provider_name():
    """Shablonlarda ko'rsatish uchun — foydalanuvchiga qaysi tashqi provayder
    (Gemini/Anthropic) ishlatilayotgani KO'RSATILMAYDI, faqat platforma
    nomi ('SHATS AI') ko'rsatiladi. Texnik jihatdan qaysi provayder ishlatilishi
    server ichida (loglarda, .env sozlamalarida) bilinadi, lekin foydalanuvchi
    tomonidan ko'rinadigan brendlash yagona bo'lishi kerak."""
    if is_gemini_configured() or is_anthropic_configured():
        return "SHATS AI"
    return None


# ------------------------------------------------------------------
# GOOGLE GEMINI (tekin tarif)
# ------------------------------------------------------------------
def _call_gemini(system_prompt, user_message, history, images, fallback):
    contents = []
    for h in (history or [])[-8:]:
        role = "model" if h["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": h["content"]}]})

    parts = []
    if user_message:
        parts.append({"text": user_message})
    elif not images:
        parts.append({"text": "Salom"})
    for img in (images or [])[:4]:
        parts.append({
            "inline_data": {
                "mime_type": img.get("media_type", "image/jpeg"),
                "data": img["data"],
            }
        })
    if not user_message and images:
        parts.insert(0, {"text": "Bu rasmda nima ko'rsatilgan? Tahlil qiling."})
    contents.append({"role": "user", "parts": parts})

    # 2026-06'dan boshlab Google kalitlarni URL parametri (?key=) o'rniga
    # so'rov sarlavhasi (header) orqali talab qiladi — ayniqsa yangi "Auth"
    # (AQ. bilan boshlanuvchi) kalitlar bilan ?key= ISHLAMAYDI.
    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    body = {
        "contents": contents,
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {"maxOutputTokens": 1500 if images else 900, "temperature": 0.7},
    }
    resp = requests.post(url, json=body, headers=headers, timeout=45)

    # "Model band" (503) — ko'pincha bir necha soniyada o'tib ketadi, shuning
    # uchun darhol taslim bo'lmasdan qisqa kutib 1 marta qayta urinib ko'ramiz.
    if resp.status_code == 503:
        import time as _time
        _time.sleep(2.5)
        resp = requests.post(url, json=body, headers=headers, timeout=45)

    if resp.status_code == 429:
        return ("Gemini bepul tarifining kunlik/daqiqalik so'rov chegarasiga yetdik. "
                "Birozdan (1 daqiqadan) so'ng qayta urinib ko'ring."), False
    if resp.status_code in (401, 403):
        return ("Gemini API kaliti qabul qilinmadi (401/403). GEMINI_API_KEY to'g'ri nusxalanganini "
                "va Google AI Studio'da kalit o'chirilmagan/cheklanmaganini tekshiring."), False
    if resp.status_code == 404:
        raise RuntimeError(
            f"Gemini modeli topilmadi (404): '{GEMINI_MODEL}' nomi noto'g'ri yoki Google tomonidan "
            f"eskirgan/o'chirilgan bo'lishi mumkin. .env faylida GEMINI_MODEL to'g'ri model nomiga "
            f"o'zgartirilishi kerak (masalan joriy mavjud modellar ro'yxatini Google AI Studio'dan tekshiring). "
            f"Server javobi: {resp.text[:300]}"
        )
    if resp.status_code == 400:
        raise RuntimeError(f"Gemini so'rovi rad etildi (400 — noto'g'ri so'rov formati). Server javobi: {resp.text[:300]}")
    if resp.status_code >= 500:
        raise RuntimeError(f"Gemini serverida vaqtinchalik xatolik ({resp.status_code}). Server javobi: {resp.text[:300]}")
    resp.raise_for_status()
    data = resp.json()

    candidates = data.get("candidates") or []
    if not candidates:
        block_reason = (data.get("promptFeedback") or {}).get("blockReason")
        if block_reason:
            return ("So'rov Gemini xavfsizlik filtridan o'tmadi. Iltimos, savolingizni boshqacha shaklda yozing."), False
        return fallback, False

    cand = candidates[0]
    finish_reason = cand.get("finishReason", "")
    text_parts = [p.get("text", "") for p in cand.get("content", {}).get("parts", []) if p.get("text")]
    reply = "\n".join(text_parts).strip()
    if not reply:
        if finish_reason == "SAFETY":
            return ("Javob xavfsizlik siyosati sababli qaytarilmadi. Savolingizni boshqacha shaklda qayta yozing."), False
        return fallback, False
    return reply, True


# ------------------------------------------------------------------
# ANTHROPIC CLAUDE (zaxira, pullik)
# ------------------------------------------------------------------
def _call_anthropic(system_prompt, user_message, history, images, fallback):
    import anthropic
    client = anthropic.Anthropic()
    messages = []
    for h in (history or [])[-8:]:
        messages.append({"role": h["role"], "content": h["content"]})

    if images:
        content = []
        for img in images[:4]:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.get("media_type", "image/jpeg"),
                    "data": img["data"],
                },
            })
        content.append({"type": "text", "text": user_message or "Bu rasmda nima ko'rsatilgan? Tahlil qiling."})
        messages.append({"role": "user", "content": content})
    else:
        messages.append({"role": "user", "content": user_message})

    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=1500 if images else 800,
        system=system_prompt,
        messages=messages,
    )
    text_parts = [b.text for b in resp.content if getattr(b, "type", "") == "text"]
    reply = "\n".join(text_parts).strip() or fallback
    return reply, True


def call_ai_assistant(assistant_type, user_message, history=None, system_override=None, images=None):
    """assistant_type: umumiy|kod|cyber|design|cloud|tarix|smm|targetolog|logistika
    system_override: maxsus system prompt (SMM/Logistika uchun)
    images: ixtiyoriy — [{"media_type": "image/png", "data": "<base64>"}...] ro'yxati.
            Foydalanuvchi rasm yuklasa, AI'ning vision (ko'rish) qobiliyati orqali
            rasmni ham tahlil qiladi (masalan kod skrinshoti, xato xabari, diagramma).
    Qaytaradi: (reply_text, is_live: bool)
    """
    system_prompt = system_override or ASSISTANT_PROMPTS.get(assistant_type, ASSISTANT_PROMPTS["umumiy"])
    fallback = FALLBACK_REPLIES.get(assistant_type, FALLBACK_REPLIES["umumiy"])

    if not is_ai_configured():
        if images:
            return ("Demo rejim: rasm tahlili uchun ham haqiqiy AI kaliti (GEMINI_API_KEY yoki ANTHROPIC_API_KEY) "
                     "kerak. Administrator .env fayliga kalitni qo'shgach, rasmlarni to'liq tahlil qila olaman."), False
        return fallback, False

    # Ustuvorlik: avval Gemini (tekin), keyin Anthropic (zaxira, pullik)
    if is_gemini_configured():
        try:
            return _call_gemini(system_prompt, user_message, history, images, fallback)
        except Exception as e:
            print(f"[AI] Gemini xatosi: {type(e).__name__}: {e}")
            if is_anthropic_configured():
                try:
                    return _call_anthropic(system_prompt, user_message, history, images, fallback)
                except Exception as e2:
                    print(f"[AI] Anthropic (zaxira) ham xato berdi: {type(e2).__name__}: {e2}")
            return _error_message(e), False

    try:
        return _call_anthropic(system_prompt, user_message, history, images, fallback)
    except Exception as e:
        print(f"[AI] Anthropic xatosi: {type(e).__name__}: {e}")
        return _error_message(e), False


# ------------------------------------------------------------------
# AI RASM GENERATSIYASI (faqat Gemini — Anthropic rasm yaratmaydi,
# faqat mavjud rasmlarni tahlil qiladi/"ko'radi")
# ------------------------------------------------------------------
def generate_image(prompt: str):
    """Gemini rasm-generatsiya modeli orqali matndan rasm yaratadi.
    Qaytaradi: (image_base64: str | None, mime_type: str | None, error: str | None)"""
    if not is_gemini_configured():
        return None, None, ("AI rasm generatsiyasi uchun GEMINI_API_KEY kerak (Anthropic rasm yaratmaydi, "
                              "faqat Gemini). Administrator .env fayliga qo'shishi kerak.")
    url = f"{GEMINI_API_BASE}/{GEMINI_IMAGE_MODEL}:generateContent"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=60)
    except requests.exceptions.RequestException as e:
        return None, None, _error_message(e)

    if resp.status_code == 429:
        return None, None, "Gemini bepul tarifining chegarasiga yetdik. Birozdan so'ng qayta urinib ko'ring."
    if resp.status_code in (401, 403):
        return None, None, "Gemini API kaliti qabul qilinmadi (401/403)."
    if resp.status_code == 404:
        return None, None, (f"Rasm generatsiya modeli topilmadi ('{GEMINI_IMAGE_MODEL}'). .env faylida "
                              f"GEMINI_IMAGE_MODEL to'g'ri model nomiga sozlanganini tekshiring.")
    if not resp.ok:
        return None, None, f"Gemini xatosi ({resp.status_code}): {resp.text[:200]}"

    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        block_reason = (data.get("promptFeedback") or {}).get("blockReason")
        if block_reason:
            return None, None, "So'rov xavfsizlik filtridan o'tmadi. Boshqacha ta'rif bilan qayta urinib ko'ring."
        return None, None, "AI rasm yarata olmadi (bo'sh javob)."

    parts = candidates[0].get("content", {}).get("parts", [])
    for p in parts:
        inline = p.get("inlineData") or p.get("inline_data")
        if inline and inline.get("data"):
            return inline["data"], inline.get("mimeType", inline.get("mime_type", "image/png")), None
    return None, None, "AI javobida rasm topilmadi — ta'rifni aniqroq yozib qayta urinib ko'ring."
