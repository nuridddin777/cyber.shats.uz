# ============================================================
# EDU ORGS — Maktab / Texnikum / O'quv markazi biznes-logikasi
# ============================================================
# Bu modul database/migrate_v28_edu_orgs.py orqali yaratilgan jadvallar
# ustida ishlaydi. Asosiy vazifalar:
#   1) Tashkilot @username generatsiyasi (masalan "18-IDUM" -> "18idum")
#   2) O'qituvchi (2 xonali) va o'quvchi (5 xonali) ID larini har bir
#      tashkilot uchun ALOHIDA, ketma-ket generatsiya qilish
#   3) Login formati: <login>@<org_username>  (@gmail.com EMAS)
#   4) Tarif limitlarini tekshirish (necha o'qituvchi/o'quvchi qo'shish mumkin)
#   5) Coin o'tkazma komissiyasini hisoblash
#   6) "5 tanga bepul jo'natish" — 1 martalik limit va uni qayta ochish
#
# Diqqat: bu fayl app.py ichidagi route'larga hali ulanmagan — bu keyingi
# bosqich ("Edu ro'yxatdan o'tish va login tizimi" / route+HTML qismi).
# Hozircha faqat sof biznes-logika va DB qatlami tayyorlandi.

import re
import secrets
import sqlite3
import datetime
from werkzeug.security import generate_password_hash


class EduOrgError(Exception):
    """Edu tashkilot logikasidagi nazorat qilinadigan xatolar uchun."""
    pass


# ------------------------------------------------------------------
# 1) Username / login yordamchilari
# ------------------------------------------------------------------
def slugify_username(raw: str) -> str:
    """
    Tashkilot nomidan @username hosil qiladi.
    Masalan: "18-IDUM" -> "18idum", "1-son texnikum" -> "1sontexnikum"
    Faqat lotin harflari va raqamlar qoladi, bo'sh joy/tire olib tashlanadi.
    """
    raw = raw.strip().lower()
    replacements = {
        "o'": "o", "g'": "g", "ʻ": "", "ʼ": "", "'": "", "`": "",
        "ў": "o", "ғ": "g", "қ": "q", "ҳ": "h",
    }
    for k, v in replacements.items():
        raw = raw.replace(k, v)
    raw = re.sub(r"[^a-z0-9]", "", raw)
    if not raw:
        raise EduOrgError("Tashkilot nomidan yaroqli username hosil bo'lmadi")
    return raw


def ensure_unique_username(conn: sqlite3.Connection, base_username: str) -> str:
    """Agar shu username band bo'lsa, oxiriga raqam qo'shib beradi (18idum, 18idum2, ...)."""
    username = base_username
    n = 2
    while conn.execute("SELECT 1 FROM edu_organizations WHERE username=?", (username,)).fetchone():
        username = f"{base_username}{n}"
        n += 1
    return username


def clean_login(login: str) -> str:
    """Login matnini tozalaydi (faqat lotin harf/raqam/nuqta/pastki chiziq).
    ENDI @tashkilot_username QO'SHILMAYDI — login endi BUTUN TIZIM bo'yicha
    o'zi mustaqil, global noyob bo'lishi kerak (chunki o'qituvchi/o'quvchi
    allaqachon RO'YXATDAN O'TISH bosqichida markaz kodi orqali aniq bir
    tashkilotga biriktiriladi — kirishda tashkilot nomini alohida
    ko'rsatish shart emas va faqat chalkashlik/xato keltirib chiqargan)."""
    login = re.sub(r"[^a-z0-9._]", "", login.strip().lower())
    if not login:
        raise EduOrgError("Login bo'sh bo'lishi mumkin emas")
    if len(login) < 3:
        raise EduOrgError("Login kamida 3 ta belgidan iborat bo'lishi kerak")
    return login


def check_login_available(conn, login: str, exclude_teacher_id=None, exclude_student_id=None):
    """Login BUTUN TIZIM bo'yicha (barcha tashkilotlar, o'qituvchi/o'quvchi/
    markaz hisoblari orasida) band emasligini tekshiradi — @ belgisi
    olib tashlangani uchun endi bitta umumiy 'nomlar maydoni' bor."""
    org_clash = conn.execute("SELECT 1 FROM edu_organizations WHERE login=?", (login,)).fetchone()
    if org_clash:
        raise EduOrgError("Bu login band (tashkilot hisobi tomonidan ishlatilgan). Boshqa login tanlang.")

    t_sql = "SELECT 1 FROM edu_teachers WHERE full_login=?"
    t_args = [login]
    if exclude_teacher_id:
        t_sql += " AND id!=?"
        t_args.append(exclude_teacher_id)
    if conn.execute(t_sql, tuple(t_args)).fetchone():
        raise EduOrgError("Bu login band. Boshqa login tanlang.")

    s_sql = "SELECT 1 FROM edu_students WHERE full_login=?"
    s_args = [login]
    if exclude_student_id:
        s_sql += " AND id!=?"
        s_args.append(exclude_student_id)
    if conn.execute(s_sql, tuple(s_args)).fetchone():
        raise EduOrgError("Bu login band. Boshqa login tanlang.")


# ------------------------------------------------------------------
# 1.1) Markaz (tashkilot) uchun global ID va ulanish kodi
# ------------------------------------------------------------------
def next_org_number(conn: sqlite3.Connection) -> str:
    """Har bir yangi tashkilotga beriladigan, ketma-ket, 5 xonali,
    BUTUN TIZIM bo'yicha YAGONA raqam (masalan '10001', '10002', ...).
    Admin CODE chiqarayotganda tashkilotni shu raqam orqali topadi."""
    conn.execute("UPDATE edu_org_number_counter SET next_number = next_number + 1 WHERE id=1")
    row = conn.execute("SELECT next_number - 1 AS n FROM edu_org_number_counter WHERE id=1").fetchone()
    return str(row["n"])


def generate_connect_code(conn: sqlite3.Connection) -> str:
    """O'qituvchi/o'quvchi ANIQ shu tashkilotga ulanib ro'yxatdan o'tishi
    uchun ishlatiladigan, taxmin qilib bo'lmaydigan, YAGONA kod.
    Faqat tarif FAOLLASHTIRILGANDA (sotib olinganda yoki 9 xonali kalit
    bilan ochilganda) generatsiya qilinadi — shunga qadar hech kim
    ulana olmaydi."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # chalkash harflar (0/O, 1/I) chiqarib tashlandi
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        exists = conn.execute(
            "SELECT 1 FROM edu_organizations WHERE connect_code=?", (code,)
        ).fetchone()
        if not exists:
            return code
    raise EduOrgError("Ulanish kodini generatsiya qilib bo'lmadi, qayta urinib ko'ring")


# ------------------------------------------------------------------
# 1.1) SINF/BO'LIM (maktab) va KURS (texnikum) tizimi
# ------------------------------------------------------------------
def generate_class_join_code(conn: sqlite3.Connection) -> str:
    """Har bir aniq sinf/bo'lim (masalan 5-A) yoki kurs (masalan 1-kurs)
    uchun ALOHIDA, taxmin qilib bo'lmaydigan ulanish kodi. Umumiy markaz
    ulanish kodidan farqli — bu kod faqat SHU sinf/kursga o'quvchini
    biriktiradi."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    for _ in range(20):
        code = "".join(secrets.choice(alphabet) for _ in range(7))
        exists = conn.execute("SELECT 1 FROM edu_org_groups WHERE join_code=?", (code,)).fetchone()
        if not exists:
            return code
    raise EduOrgError("Sinf kodini generatsiya qilib bo'lmadi, qayta urinib ko'ring")


VALID_SECTION_LETTERS = list("ABVGDЕЖZ")  # A,B,V... — lotin+ozgina kirill uyg'unlashtirilgan, oddiy A-Z ham ishlaydi


def create_school_classes(conn: sqlite3.Connection, org_id: int, grade_no: int, section_letters: list,
                           subject_id: int = None) -> list:
    """Maktab uchun: bitta sinf raqami (5-11) + bir nechta bo'lim harfi
    (masalan ['A','B','V']) beriladi -> har biri uchun ALOHIDA guruh
    (masalan '5-A', '5-B', '5-V'), o'zining join_code'i bilan yaratiladi.
    Qaytaradi: yaratilgan guruh dictlari ro'yxati."""
    if grade_no < 5 or grade_no > 11:
        raise EduOrgError("Sinf raqami 5 dan 11 gacha bo'lishi kerak")
    if not section_letters:
        raise EduOrgError("Kamida bitta bo'lim (masalan A) kiritilishi kerak")

    created = []
    for letter in section_letters:
        letter = letter.strip().upper()
        if not letter:
            continue
        name = f"{grade_no}-{letter}"
        existing = conn.execute(
            "SELECT id FROM edu_org_groups WHERE org_id=? AND grade_no=? AND section_letter=?",
            (org_id, grade_no, letter)
        ).fetchone()
        if existing:
            continue  # bu sinf-bo'lim allaqachon mavjud, qayta yaratilmaydi
        code = generate_class_join_code(conn)
        conn.execute(
            "INSERT INTO edu_org_groups (org_id, name, subject_id, grade_no, section_letter, join_code) "
            "VALUES (?,?,?,?,?,?)",
            (org_id, name, subject_id, grade_no, letter, code)
        )
        gid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        created.append({"id": gid, "name": name, "join_code": code})
    conn.commit()
    if not created:
        raise EduOrgError("Bu sinf-bo'limlar allaqachon mavjud")
    return created


def create_texnikum_course(conn: sqlite3.Connection, org_id: int, kurs_no: int, subject_id: int = None) -> dict:
    """Texnikum uchun: 1-kurs yoki 2-kurs guruhini (bo'limsiz) yaratadi,
    o'zining join_code'i bilan."""
    if kurs_no not in (1, 2):
        raise EduOrgError("Kurs raqami 1 yoki 2 bo'lishi kerak")
    name = f"{kurs_no}-kurs"
    existing = conn.execute(
        "SELECT id FROM edu_org_groups WHERE org_id=? AND grade_no=? AND section_letter IS NULL",
        (org_id, kurs_no)
    ).fetchone()
    if existing:
        raise EduOrgError(f"'{name}' allaqachon mavjud")
    code = generate_class_join_code(conn)
    conn.execute(
        "INSERT INTO edu_org_groups (org_id, name, subject_id, grade_no, section_letter, join_code) "
        "VALUES (?,?,?,?,NULL,?)",
        (org_id, name, subject_id, kurs_no, code)
    )
    gid = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
    conn.commit()
    return {"id": gid, "name": name, "join_code": code}


def resolve_class_code(conn: sqlite3.Connection, code: str):
    """O'quvchi kiritgan sinf/kurs kodini tekshiradi. Kod TO'G'RI bo'lsa ham,
    tashkilot hali tarif sotib olmagan (is_active=0) bo'lsa ISHLAMAYDI —
    xuddi umumiy markaz ulanish kodi kabi, faqat tarif faollashtirilgach
    ishlaydi. Qaytaradi: (org_row, group_row)."""
    code = (code or "").strip().upper()
    if not code:
        raise EduOrgError("Sinf/kurs kodini kiriting")
    group = conn.execute("SELECT * FROM edu_org_groups WHERE join_code=?", (code,)).fetchone()
    if not group:
        raise EduOrgError("Bunday sinf/kurs kodi topilmadi")
    org = conn.execute(
        "SELECT * FROM edu_organizations WHERE id=? AND is_active=1", (group["org_id"],)
    ).fetchone()
    if not org:
        raise EduOrgError("Ushbu markaz hali faol emas (tarif sotib olinmagan) — kod hozircha ishlamaydi")
    return org, group


def list_org_classes(conn: sqlite3.Connection, org_id: int):
    """Tashkilotning barcha sinf/bo'lim/kurs guruhlarini (join_code bilan) qaytaradi."""
    return conn.execute(
        "SELECT * FROM edu_org_groups WHERE org_id=? AND join_code IS NOT NULL "
        "ORDER BY grade_no, section_letter", (org_id,)
    ).fetchall()


# ------------------------------------------------------------------
# 2) Tashkilotni ro'yxatdan o'tkazish
# ------------------------------------------------------------------
def register_organization(conn, org_type, name, region_id, district_id,
                           phone, login, password, email="", telegram_user=""):
    """
    Maktab/Texnikum/O'quv markazini ro'yxatdan o'tkazadi.
    Tarif sotib olinmaguncha is_active=0 bo'ladi (panellar yopiq).
    Qaytaradi: yangi tashkilot ID.
    """
    if org_type not in ("maktab", "texnikum", "oquv_markazi"):
        raise EduOrgError("Noto'g'ri tashkilot turi")

    login = clean_login(login)
    check_login_available(conn, login)

    base_username = slugify_username(name)
    username = ensure_unique_username(conn, base_username)

    if telegram_user and not telegram_user.startswith("@"):
        telegram_user = "@" + telegram_user

    try:
        cur = conn.execute("""
            INSERT INTO edu_organizations
                (org_type, name, username, region_id, district_id, phone,
                 login, password_hash, email, telegram_user, is_active)
            VALUES (?,?,?,?,?,?,?,?,?,?,0)
        """, (org_type, name.strip(), username, region_id, district_id, phone,
              login, generate_password_hash(password), email, telegram_user))
    except sqlite3.IntegrityError:
        # Himoya qatlami: yuqoridagi check_login_available bilan bu yerga
        # yetib kelish orasida (juda kam ehtimol, lekin nazariy jihatdan
        # mumkin) boshqa so'rov xuddi shu loginni band qilib ulgurgan bo'lsa —
        # xom sqlite3.IntegrityError o'rniga tushunarli xabar bilan
        # EduOrgError chiqaramiz (bu esa 500 xato o'rniga chiroyli xabar
        # ko'rsatiladi).
        raise EduOrgError("Bu login band. Boshqa login tanlang.")
    org_id = cur.lastrowid

    org_number = next_org_number(conn)
    conn.execute("UPDATE edu_organizations SET org_number=? WHERE id=?", (org_number, org_id))

    conn.execute("INSERT INTO edu_org_id_counters (org_id, teacher_seq, student_seq) VALUES (?,0,0)", (org_id,))
    conn.commit()
    return org_id


def activate_organization_tariff(conn, org_id, tarif_code, months=1):
    """
    Tarif sotib olingandan keyin chaqiriladi -> is_active=1, panellar ochiladi.

    HAQIQIY SOTIB OLISH: tarifning narxi (edu_tariffs.price_coins) tashkilot
    balansidan (edu_organizations.coin_balance) yechiladi va YAGONA G'azna
    jamg'armasiga tushadi (charge_org_coins orqali — xuddi qo'shimcha
    o'qituvchi/o'quvchi sotib olishdagi bilan bir xil mexanizm). Agar
    tashkilot balansida yetarli CODE bo'lmasa, EduOrgError qaytariladi va
    tarif FAOLLASHTIRILMAYDI (avval G'aznadan CODE olish kerak).

    `months` necha oyga sotib olinayotganini bildiradi — narx shunga
    ko'paytiriladi (masalan 2 oyga = 2 x price_coins).
    2 oyga sotib olinsa (months>=2) — bir martalik qo'shimcha "5 tanga
    sovg'a" beriladi (mavjud qoida, o'zgarishsiz qoldi).
    """
    tarif = conn.execute("SELECT * FROM edu_tariffs WHERE code=?", (tarif_code,)).fetchone()
    if not tarif:
        raise EduOrgError("Bunday tarif topilmadi")

    months = max(int(months or 1), 1)
    total_cost = (tarif["price_coins"] or 0) * months

    if total_cost > 0:
        org = conn.execute("SELECT coin_balance FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
        if not org:
            raise EduOrgError("Tashkilot topilmadi")
        if org["coin_balance"] < total_cost:
            raise EduOrgError(
                f"Balans yetarli emas: '{tarif['display_name']}' tarifi {months} oyga "
                f"{total_cost} CODE turadi, tashkilot balansida {org['coin_balance']} CODE bor. "
                f"Avval G'aznadan CODE oldiring."
            )
        from edu_treasury_bridge import charge_org_coins  # lazy import — aylanma import'dan qochish
        charge_org_coins(conn, org_id, total_cost, f"edu_tariff_purchase:{tarif_code}")

    conn.execute("""
        UPDATE edu_organizations
        SET tarif_code=?, is_active=1,
            monitoring_panel_enabled=?, support_panel_enabled=?,
            subscription_started_at=datetime('now'),
            subscription_expires_at=datetime('now', ?)
        WHERE id=?
    """, (tarif_code, tarif["has_monitoring_panel"], tarif["has_support_panel"],
          f"+{months} months", org_id))

    # Ulanish kodi hali yo'q bo'lsa (birinchi marta faollashtirilyapti) — generatsiya qilamiz.
    # Bu kod bo'lmasa o'qituvchi/o'quvchi hech qachon ro'yxatdan o'ta olmaydi.
    org_row = conn.execute("SELECT connect_code FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if not org_row["connect_code"]:
        code = generate_connect_code(conn)
        conn.execute("UPDATE edu_organizations SET connect_code=? WHERE id=?", (code, org_id))

    if months >= 2:
        _grant_extra_gift(conn, org_id)

    conn.commit()


def activate_tariff_with_key(conn, org_id, key_code):
    """
    Tarifni COIN sarflamasdan, G'azna (Edu Treasury) tomonidan chiqarilgan
    9 xonali BIR MARTALIK faollashtirish kaliti orqali ochadi.
    Kalit topilmasa, ishlatilgan bo'lsa yoki mos kelmasa — xato qaytariladi.
    """
    from edu_treasury_bridge import mark_activation_key_used  # aylanma import'dan qochish

    key = conn.execute(
        "SELECT * FROM edu_activation_keys WHERE key_code=?", (key_code.strip(),)
    ).fetchone()
    if not key:
        raise EduOrgError("Bunday faollashtirish kaliti topilmadi")
    if key["is_used"]:
        raise EduOrgError("Bu kalit allaqachon ishlatilgan")

    tarif = conn.execute("SELECT * FROM edu_tariffs WHERE code=?", (key["tarif_code"],)).fetchone()
    if not tarif:
        raise EduOrgError("Kalitga bog'langan tarif topilmadi")

    conn.execute("""
        UPDATE edu_organizations
        SET tarif_code=?, is_active=1,
            monitoring_panel_enabled=?, support_panel_enabled=?,
            subscription_started_at=datetime('now'),
            subscription_expires_at=datetime('now', ?)
        WHERE id=?
    """, (tarif["code"], tarif["has_monitoring_panel"], tarif["has_support_panel"],
          f"+{key['months']} months", org_id))

    org_row = conn.execute("SELECT connect_code FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if not org_row["connect_code"]:
        code = generate_connect_code(conn)
        conn.execute("UPDATE edu_organizations SET connect_code=? WHERE id=?", (code, org_id))

    if key["months"] >= 2:
        _grant_extra_gift(conn, org_id)

    mark_activation_key_used(conn, key["id"], org_id)
    conn.commit()
    return tarif


def check_and_expire_subscription(conn, org_id):
    """
    Tashkilot faol (is_active=1) va subscription_expires_at o'tib ketgan
    bo'lsa, tarifni avtomatik o'chiradi (is_active=0). 1 oylik, 1 yillik
    yoki istalgan necha oylik tarif sotib olinganda subscription_expires_at
    shu muddatga o'rnatiladi (activate_organization_tariff /
    activate_tariff_with_key) — bu funksiya shu muddat o'tganini tekshiradi.

    `connect_code` ATAYLAB o'chirilmaydi — tarif qayta sotib olinganda
    eski kod bilan davom etilishi uchun, lekin registratsiya/ulanish
    yo'llarining barchasi is_active=1 talab qiladi, shuning uchun muddati
    tugagan markazga hech kim ulana olmaydi (yangi tarif sotib olinmaguncha).

    Qaytaradi: True — agar shu chaqiriqda muddati tugab, o'chirilgan bo'lsa.
    """
    org = conn.execute(
        "SELECT is_active, subscription_expires_at FROM edu_organizations WHERE id=?", (org_id,)
    ).fetchone()
    if not org or not org["is_active"] or not org["subscription_expires_at"]:
        return False

    try:
        expires_at = datetime.datetime.fromisoformat(org["subscription_expires_at"])
    except (TypeError, ValueError):
        return False

    if datetime.datetime.now() > expires_at:
        conn.execute("UPDATE edu_organizations SET is_active=0 WHERE id=?", (org_id,))
        conn.commit()
        return True
    return False


def _grant_extra_gift(conn, org_id):
    """
    2 oylik tarif sotib olinganda tashkilotdagi HAMMA o'qituvchi/o'quvchiga
    qo'shimcha 1 martalik "5 tanga bepul jo'natish" huquqi beriladi.
    """
    teachers = conn.execute("SELECT id FROM edu_teachers WHERE org_id=?", (org_id,)).fetchall()
    students = conn.execute("SELECT id FROM edu_students WHERE org_id=?", (org_id,)).fetchall()
    for t in teachers:
        _add_gift_credit(conn, "teacher", t["id"])
    for s in students:
        _add_gift_credit(conn, "student", s["id"])


def _add_gift_credit(conn, user_type, user_id):
    row = conn.execute(
        "SELECT remaining_gifts FROM edu_gift_code_usage WHERE user_type=? AND user_id=?",
        (user_type, user_id)).fetchone()
    if row:
        conn.execute(
            "UPDATE edu_gift_code_usage SET remaining_gifts=remaining_gifts+1, updated_at=datetime('now') WHERE user_type=? AND user_id=?",
            (user_type, user_id))
    else:
        conn.execute(
            "INSERT INTO edu_gift_code_usage (user_type, user_id, remaining_gifts) VALUES (?,?,1)",
            (user_type, user_id))


# ------------------------------------------------------------------
# 3) ID generatsiyasi (har tashkilot uchun ALOHIDA hisoblanadi)
# ------------------------------------------------------------------
def _next_seq(conn, org_id, column):
    """edu_org_id_counters jadvalidagi tegishli ustunni +1 qilib qaytaradi."""
    conn.execute(f"UPDATE edu_org_id_counters SET {column} = {column} + 1 WHERE org_id=?", (org_id,))
    row = conn.execute(f"SELECT {column} FROM edu_org_id_counters WHERE org_id=?", (org_id,)).fetchone()
    return row[0]


def next_teacher_number(conn, org_id):
    """2 xonali ketma-ket raqam: '01', '02', ... '99', keyin '100' (agar 99dan oshsa)."""
    seq = _next_seq(conn, org_id, "teacher_seq")
    return f"{seq:02d}"


def next_student_number(conn, org_id):
    """5 xonali ketma-ket raqam: '00001', '00002', ..."""
    seq = _next_seq(conn, org_id, "student_seq")
    return f"{seq:05d}"


# ------------------------------------------------------------------
# 4) Tarif limitlarini tekshirish
# ------------------------------------------------------------------
def get_org_tariff(conn, org_id):
    org = conn.execute("SELECT * FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if not org:
        raise EduOrgError("Tashkilot topilmadi")
    if not org["is_active"] or not org["tarif_code"]:
        raise EduOrgError("Tashkilot tarif sotib olmagan — panellar yopiq")
    tarif = conn.execute("SELECT * FROM edu_tariffs WHERE code=?", (org["tarif_code"],)).fetchone()
    if not tarif:
        raise EduOrgError("Tarif ma'lumoti topilmadi")
    return org, tarif


def check_can_add_teacher(conn, org_id):
    """
    Yangi o'qituvchi qo'shish mumkinmi tekshiradi.
    Qaytaradi: (mumkinmi, coin_narxi, sabab)
    """
    org, tarif = get_org_tariff(conn, org_id)
    current = conn.execute("SELECT COUNT(*) c FROM edu_teachers WHERE org_id=? AND is_active=1", (org_id,)).fetchone()["c"]

    if current < tarif["max_teachers"]:
        return True, 0, "Tarif limiti ichida"

    extra_used = current - tarif["max_teachers"]
    if tarif["max_extra_teachers"] and extra_used < tarif["max_extra_teachers"]:
        return True, tarif["extra_teacher_coin_cost"], "Qo'shimcha o'qituvchi (coin evaziga)"

    return False, 0, "O'qituvchilar soni limiti va qo'shimcha slotlar tugagan"


def check_can_add_student(conn, org_id, count=1):
    """
    `count` ta o'quvchi qo'shilganda kerak bo'ladigan qo'shimcha coin narxini hisoblaydi.
    Standart limit ichidagi o'quvchilar bepul, undan oshgan HAR bir
    extra_student_group_size (masalan 5) ta uchun 1 coin olinadi.
    Qaytaradi: (mumkinmi, kerakli_coin, sabab)
    """
    org, tarif = get_org_tariff(conn, org_id)
    current = conn.execute("SELECT COUNT(*) c FROM edu_students WHERE org_id=? AND is_active=1", (org_id,)).fetchone()["c"]
    new_total = current + count

    if new_total <= tarif["max_students"]:
        return True, 0, "Tarif limiti ichida"

    over_limit_count = new_total - tarif["max_students"]
    group_size = tarif["extra_student_group_size"] or 5
    needed_coins = -(-over_limit_count // group_size) * tarif["extra_student_coin_cost"]  # ceil division
    return True, needed_coins, f"{over_limit_count} ta o'quvchi limitdan tashqari — {needed_coins} coin talab qilinadi"


# ------------------------------------------------------------------
# 5) O'qituvchi / o'quvchi ro'yxatdan o'tkazish
# ------------------------------------------------------------------
def register_teacher(conn, org_id, familiya, ism, subject_id, login, password, region_id, district_id):
    can_add, coin_cost, reason = check_can_add_teacher(conn, org_id)
    if not can_add:
        raise EduOrgError(reason)

    org = conn.execute("SELECT username, coin_balance FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if coin_cost:
        if org["coin_balance"] < coin_cost:
            raise EduOrgError(f"Qo'shimcha o'qituvchi uchun {coin_cost} coin kerak, balans yetarli emas")
        from edu_treasury_bridge import charge_org_coins  # lazy import — aylanma import'dan qochish uchun
        charge_org_coins(conn, org_id, coin_cost, "edu_extra_teacher")

    teacher_number = next_teacher_number(conn, org_id)
    clean = clean_login(login)
    check_login_available(conn, clean)

    try:
        cur = conn.execute("""
            INSERT INTO edu_teachers
                (org_id, teacher_number, familiya, ism, subject_id, login, full_login,
                 password_hash, region_id, district_id, is_extra_slot)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (org_id, teacher_number, familiya.strip(), ism.strip(), subject_id,
              clean, clean, generate_password_hash(password),
              region_id, district_id, 1 if coin_cost else 0))
    except sqlite3.IntegrityError:
        raise EduOrgError("Bu login band. Boshqa login tanlang.")

    _add_gift_credit(conn, "teacher", cur.lastrowid)
    conn.commit()
    return {"id": cur.lastrowid, "teacher_number": teacher_number, "full_login": clean}


def register_student(conn, org_id, familiya, ism, group_id, login, password, region_id, district_id):
    can_add, coin_cost, reason = check_can_add_student(conn, org_id, count=1)
    if not can_add:
        raise EduOrgError(reason)

    org = conn.execute("SELECT username, coin_balance FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if coin_cost:
        if org["coin_balance"] < coin_cost:
            raise EduOrgError(f"Qo'shimcha o'quvchi uchun {coin_cost} coin kerak, balans yetarli emas")
        from edu_treasury_bridge import charge_org_coins
        charge_org_coins(conn, org_id, coin_cost, "edu_extra_student")

    student_number = next_student_number(conn, org_id)
    clean = clean_login(login)
    check_login_available(conn, clean)

    try:
        cur = conn.execute("""
            INSERT INTO edu_students
                (org_id, student_number, familiya, ism, group_id, login, full_login,
                 password_hash, region_id, district_id)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (org_id, student_number, familiya.strip(), ism.strip(), group_id,
              clean, clean, generate_password_hash(password),
              region_id, district_id))
    except sqlite3.IntegrityError:
        raise EduOrgError("Bu login band. Boshqa login tanlang.")

    _add_gift_credit(conn, "student", cur.lastrowid)
    conn.commit()
    return {"id": cur.lastrowid, "student_number": student_number, "full_login": clean}


# ------------------------------------------------------------------
# 6) Coin o'tkazma komissiyasi
# ------------------------------------------------------------------
def calc_transfer_commission(conn, amount):
    """
    Texnik topshiriqdagi komissiya jadvali bo'yicha hisoblaydi:
      <=9   -> 0
      10-19 -> 1, 20-29 -> 2, ... 90-99 -> 9, 100-200 -> 15
    Maksimal bir martalik o'tkazma: 200 coin.
    """
    if amount <= 0:
        raise EduOrgError("Miqdor musbat bo'lishi kerak")
    if amount > 200:
        raise EduOrgError("Bir martalik o'tkazma maksimal 200 tanga")

    row = conn.execute(
        "SELECT commission_coins FROM edu_coin_commission WHERE ? BETWEEN min_amount AND max_amount",
        (amount,)).fetchone()
    return row["commission_coins"] if row else 0


def can_send_free_gift(conn, user_type, user_id):
    """Foydalanuvchi 5 tanga bepul (komissiyasiz, alohida) jo'nata oladimi?"""
    row = conn.execute(
        "SELECT remaining_gifts FROM edu_gift_code_usage WHERE user_type=? AND user_id=?",
        (user_type, user_id)).fetchone()
    return bool(row and row["remaining_gifts"] > 0)


def consume_free_gift(conn, user_type, user_id):
    if not can_send_free_gift(conn, user_type, user_id):
        raise EduOrgError("5 tanga bepul jo'natish huquqi qolmagan")
    conn.execute(
        "UPDATE edu_gift_code_usage SET remaining_gifts = remaining_gifts - 1, updated_at=datetime('now') WHERE user_type=? AND user_id=?",
        (user_type, user_id))
    conn.commit()
