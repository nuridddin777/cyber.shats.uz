# ============================================================
# CYBER SHATS — Baza bilan ishlash uchun yordamchi funksiyalar
# ============================================================
import os
import re
import sqlite3
from flask import g, current_app

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

    # Translates the sqlite-flavored SQL used throughout the app (built for
    # sqlite3's `?` placeholders and datetime('now', ...) helper) so every
    # existing call site (query_one/query_all/execute, and the handful of
    # files that call conn.execute()/cur.lastrowid directly) keeps working
    # unchanged against Postgres.
    _NOW_OFFSET_RE = re.compile(r"datetime\(\s*'now'\s*,\s*'([-+]?\d+)\s+(\w+)'\s*\)", re.IGNORECASE)
    _NOW_RE = re.compile(r"datetime\(\s*'now'\s*\)", re.IGNORECASE)
    _DATETIME_WRAP_RE = re.compile(r"datetime\(([^()]+)\)", re.IGNORECASE)
    _DATE_OFFSET_RE = re.compile(r"date\(\s*'now'\s*,\s*'([-+]?\d+)\s+(\w+)'\s*\)", re.IGNORECASE)
    _DATE_NOW_RE = re.compile(r"date\(\s*'now'\s*\)", re.IGNORECASE)
    _DATE_WRAP_RE = re.compile(r"date\(([^()]+)\)", re.IGNORECASE)
    _STRFTIME_RE = re.compile(r"strftime\(\s*'([^']*)'\s*,\s*([^()]+?)\s*\)", re.IGNORECASE)
    _INSERT_OR_IGNORE_RE = re.compile(r"INSERT\s+OR\s+IGNORE\s+INTO", re.IGNORECASE)
    _INSERT_TABLE_RE = re.compile(r"INSERT\s+INTO\s+\"?(\w+)\"?", re.IGNORECASE)

    _STRFTIME_TO_TO_CHAR = {
        "%Y": "YYYY", "%m": "MM", "%d": "DD",
        "%H": "HH24", "%M": "MI", "%S": "SS",
    }

    def _strftime_fmt_to_pg(fmt):
        out = fmt
        for sqlite_code, pg_code in _STRFTIME_TO_TO_CHAR.items():
            out = out.replace(sqlite_code, pg_code)
        return out

    def _strftime_sub(m):
        fmt, expr = m.group(1), m.group(2).strip()
        pg_fmt = _strftime_fmt_to_pg(fmt)
        if expr == "'now'":
            return f"to_char(NOW() AT TIME ZONE 'UTC', '{pg_fmt}')"
        return f"to_char(({expr})::timestamp, '{pg_fmt}')"

    _table_has_id_cache = {}

    def _table_has_id(raw_conn, table):
        if table not in _table_has_id_cache:
            with raw_conn.cursor() as c:
                c.execute(
                    "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name='id'",
                    (table,),
                )
                _table_has_id_cache[table] = c.fetchone() is not None
        return _table_has_id_cache[table]

    def _translate_sql(sql):
        # created_at/expires_at/etc are TEXT columns (migrated as-is from
        # SQLite's loose typing), storing 'YYYY-MM-DD HH:MM:SS' UTC strings.
        # NOW() returns a native timestamptz, which can't compare against
        # TEXT — format it as UTC text in the exact same shape SQLite's
        # datetime('now') produced, so string comparisons keep working.
        sql = _NOW_OFFSET_RE.sub(
            r"to_char((NOW() AT TIME ZONE 'UTC') + INTERVAL '\1 \2', 'YYYY-MM-DD HH24:MI:SS')", sql
        )
        sql = _NOW_RE.sub("to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD HH24:MI:SS')", sql)
        sql = _DATETIME_WRAP_RE.sub(r"(\1)", sql)  # datetime(col) -> (col); text ISO timestamps compare fine as-is
        sql = _DATE_OFFSET_RE.sub(
            r"to_char((NOW() AT TIME ZONE 'UTC') + INTERVAL '\1 \2', 'YYYY-MM-DD')", sql
        )
        sql = _DATE_NOW_RE.sub("to_char(NOW() AT TIME ZONE 'UTC', 'YYYY-MM-DD')", sql)
        sql = _DATE_WRAP_RE.sub(lambda m: f"to_char(({m.group(1)})::timestamp, 'YYYY-MM-DD')", sql)
        sql = _STRFTIME_RE.sub(_strftime_sub, sql)
        had_or_ignore = bool(_INSERT_OR_IGNORE_RE.search(sql))
        sql = _INSERT_OR_IGNORE_RE.sub("INSERT INTO", sql)
        sql = sql.replace("?", "%s")
        return sql, had_or_ignore

    class _PGCursorAdapter:
        def __init__(self, raw_conn, cur):
            self._raw_conn = raw_conn
            self._cur = cur
            self.lastrowid = None

        def execute(self, sql, args=()):
            translated, had_or_ignore = _translate_sql(sql)
            stripped = translated.strip()
            is_insert = stripped[:6].upper() == "INSERT"
            if had_or_ignore and "ON CONFLICT" not in stripped.upper():
                stripped = stripped.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
            # MUHIM (tuzatilgan xato): "RETURNING id" faqat BIZ o'zimiz
            # qo'shgan holatdagina keyinroq avtomatik fetchone() qilinishi
            # kerak (pastda, lastrowid uchun) — agar chaqiruvchi o'zi aniq
            # RETURNING band(lar) yozgan bo'lsa (masalan
            # "INSERT ... ON CONFLICT ... RETURNING count"), natija
            # qatorini query_one()/query_all() o'zi fetchone/fetchall bilan
            # o'qishi kerak. Ilgari bu farq qilinmasdi — har qanday INSERT
            # uchun (RETURNING band'i chaqiruvchi tomonidan yozilgan bo'lsa
            # ham) natija qatori shu yerda "yeb qo'yilardi", va
            # chaqiruvchining keyingi fetchone() chaqiruvi HAR DOIM None
            # qaytarardi — garchi INSERT/UPSERT muvaffaqiyatli bo'lsa ham.
            auto_appended_returning_id = False
            if is_insert and "RETURNING" not in stripped.upper():
                m = _INSERT_TABLE_RE.search(stripped)
                table = m.group(1) if m else None
                if table and _table_has_id(self._raw_conn, table):
                    stripped = stripped.rstrip().rstrip(";") + " RETURNING id"
                    auto_appended_returning_id = True
            try:
                # psycopg2 parses %-placeholders in the query whenever a
                # `vars` argument is passed at all, even an empty tuple —
                # any literal '%' in the SQL (e.g. a LIKE 'foo:%' pattern)
                # then gets misread as a malformed format spec. sqlite3 has
                # no such issue since '?' placeholders don't overlap with
                # any other syntax. Only pass args when there actually are
                # some to bind.
                if args:
                    self._cur.execute(stripped, args)
                else:
                    self._cur.execute(stripped)
            except Exception:
                # Postgres (unlike sqlite3) poisons the WHOLE transaction after
                # any failed statement — every later query on this connection
                # would raise "current transaction is aborted" even though the
                # app's own code (e.g. friends_routes.py) wraps each query in
                # its own try/except expecting to keep going after one fails.
                # Roll back immediately so the connection stays usable.
                self._raw_conn.rollback()
                raise
            if auto_appended_returning_id:
                try:
                    row = self._cur.fetchone()
                    self.lastrowid = row["id"] if row else None
                except (psycopg2.ProgrammingError, TypeError, KeyError):
                    self.lastrowid = None
            return self

        def __getattr__(self, name):
            return getattr(self._cur, name)

    class _PGConnectionAdapter:
        """Makes a psycopg2 connection look like a sqlite3.Connection for the
        rest of the codebase: conn.execute(...), conn.commit(), row_factory
        access via dict(row)/row['col'], and cur.lastrowid after an INSERT."""

        def __init__(self, raw_conn):
            self._raw_conn = raw_conn

        def execute(self, sql, args=()):
            cur = self._raw_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            return _PGCursorAdapter(self._raw_conn, cur).execute(sql, args)

        def cursor(self, *a, **kw):
            # Wrapped, not a raw psycopg2 cursor: some files (telegram_bot.py)
            # call conn.cursor() directly and chain c.execute(sql).fetchone() —
            # psycopg2's own cursor.execute() returns None (sqlite3's returns
            # the cursor itself), and a raw cursor also skips SQL translation
            # entirely. Route through the same adapter conn.execute() uses.
            kw.setdefault("cursor_factory", psycopg2.extras.RealDictCursor)
            raw_cur = self._raw_conn.cursor(*a, **kw)
            return _PGCursorAdapter(self._raw_conn, raw_cur)

        def __getattr__(self, name):
            return getattr(self._raw_conn, name)


def get_db():
    """Joriy so'rov uchun SQLite ulanishini qaytaradi (har bir request uchun bitta).

    MUHIM (tuzatilgan JIDDIY XATO): avval bu yerda WAL (Write-Ahead
    Logging) rejimi YOQILMAGAN va busy_timeout SOZLANMAGAN edi. SQLite
    standart holatda ("rollback journal" rejimida) YOZISH vaqtida BUTUN
    faylni bloklab qo'yadi — shu payt boshqa HAR QANDAY ulanish (o'qish
    ham) darhol "database is locked" xatosi bilan yiqilardi. Bizning
    holatimizda ESA BOT (alohida, doimiy ishlaydigan jarayon — har 10
    daqiqada avtomatik tekshiruvlar, har xabar uchun yozuvlar) VA SAYT
    (har sahifa yuklanganda ham, login_streak tekshiruvi tufayli, yozish
    urinishi) BIR XIL faylga BIR VAQTDA yozishga urinishi TABIIY holat —
    va aynan shu YUZAGA KELISH ehtimoli mening KETMA-KET (bitta jarayon,
    hech qachon parallel) testlarimda HECH QACHON takrorlanmaydi, lekin
    haqiqiy serverda (bot + sayt bir vaqtda ishlaganda) TEZ-TEZ chiqishi
    mumkin edi — bu "500 xato hamma bo'limda" shikoyatining haqiqiy
    sababi bo'lishi ehtimoli katta.

    Endi: WAL rejimi — yozish paytida ham BOSHQALAR o'qishda davom eta
    oladi (deyarli hech qachon bloklanmaydi). busy_timeout=10000 —
    haqiqatan ham to'qnashuv bo'lsa, darhol xato berish o'rniga 10
    soniyagacha KUTIB, qayta urinadi.

    POSTGRES: DATABASE_URL o'rnatilgan bo'lsa (Railway), shu yerning o'zi
    bot+sayt bir xil SQLite faylga yozishdan kelib chiqqan yuqoridagi butun
    muammoni ildizidan yo'qotadi — Postgres yozishni bloklamaydi. Qolgan
    130+ fayl o'zgarishsiz ishlashi uchun ulanish yuqoridagi
    _PGConnectionAdapter bilan o'raladi (conn.execute(), cur.lastrowid,
    dict(row) hammasi ilgarigidek ishlaydi)."""
    if "db" not in g:
        if USE_POSTGRES:
            raw = psycopg2.connect(DATABASE_URL)
            raw.autocommit = False
            g.db = _PGConnectionAdapter(raw)
        else:
            g.db = sqlite3.connect(current_app.config["DB_PATH"], timeout=10)
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
            g.db.execute("PRAGMA journal_mode = WAL")
            g.db.execute("PRAGMA busy_timeout = 10000")
    return g.db


def new_connection(sqlite_path=None):
    """get_db()ning Flask `g`ga bog'liq bo'lmagan varianti — Flask so'rov
    kontekstidan tashqarida ishlaydigan kod uchun (masalan telegram_bot.py,
    o'zining doimiy fon oqimida). Chaqiruvchi .close() qilishi kerak."""
    if USE_POSTGRES:
        raw = psycopg2.connect(DATABASE_URL)
        raw.autocommit = False
        return _PGConnectionAdapter(raw)
    conn = sqlite3.connect(sqlite_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


# ------------------------------------------------------------------
# AVTOMATIK SCHEMA TEKSHIRUVI (V2 — V7 migratsiyalarining yig'indisi)
# ------------------------------------------------------------------
# Eski baza fayllarida (masalan, migrate_v6.py / migrate_v7.py qo'lda
# ishga tushirilmagan bo'lsa) ba'zi jadvallar yo'q bo'lib qoladi va
# "no such table: ..." xatosi chiqadi (masalan ping_test_usage,
# certificate_applications). Bu funksiya ilova ishga tushganda bir marta
# chaqiriladi va yetishmayotgan jadval/ustunlarni CREATE TABLE IF NOT
# EXISTS / ALTER TABLE orqali xavfsiz qo'shib qo'yadi. Mavjud ma'lumotga
# tegmaydi, faqat yo'q narsalarni qo'shadi.
def _col_exists(conn, table, col):
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def _table_exists(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def ensure_schema(db_path):
    """Baza faylida yetishmayotgan jadval/ustunlarni avtomatik yaratadi.

    POSTGRES: bu funksiya SQLite'ga xos (PRAGMA, ALTER TABLE ADD COLUMN
    ketma-ketligi) — Postgres'ga o'tgan baza allaqachon TO'LIQ, oxirgi
    holatidagi sxema bilan ko'chirilgan (barcha ustun/jadvallar bilan),
    shuning uchun bu yerda qilinadigan ish allaqachon bajarilgan. Shunchaki
    o'tkazib yuboramiz."""
    if USE_POSTGRES:
        return
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # --- users jadvaliga yetishmayotgan ustunlar (V1/V2/V4) ---
    if _table_exists(conn, "users"):
        _had_email_verified_col = _col_exists(conn, "users", "email_verified")
        for col, defn in [
            ("code_balance", "INTEGER NOT NULL DEFAULT 0"),
            ("oauth_provider", "TEXT DEFAULT ''"),
            ("last_login_ip", "TEXT DEFAULT ''"),
            ("failed_login_count", "INTEGER NOT NULL DEFAULT 0"),
            ("locked_until", "TEXT DEFAULT NULL"),
            ("custom_id", "TEXT UNIQUE DEFAULT NULL"),
            ("admin_id", "TEXT DEFAULT NULL"),
            ("treasury_password_hash", "TEXT DEFAULT NULL"),
            ("email_verified", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if not _col_exists(conn, "users", col):
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")

        # Email tasdiqlash endi qo'shildi — bu funksiya ISHGA TUSHISHDAN OLDIN
        # ro'yxatdan o'tgan mavjud foydalanuvchilarni bloklab qo'ymaslik uchun,
        # ustun YANGI qo'shilgan bo'lsa, ularni "tasdiqlangan" deb belgilaymiz.
        if not _had_email_verified_col:
            conn.execute("UPDATE users SET email_verified=1")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_admin_id "
            "ON users(admin_id) WHERE admin_id IS NOT NULL"
        )


    # --- courses / directions yetishmayotgan ustunlar ---
    if _table_exists(conn, "courses"):
        for col, defn in [
            ("code_price", "INTEGER NOT NULL DEFAULT 0"),
            ("is_pro_only", "INTEGER NOT NULL DEFAULT 0"),
            ("is_paid", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if not _col_exists(conn, "courses", col):
                conn.execute(f"ALTER TABLE courses ADD COLUMN {col} {defn}")

    if _table_exists(conn, "directions"):
        for col, defn in [
            ("is_pro_only", "INTEGER NOT NULL DEFAULT 0"),
            ("is_cyber_pro_only", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            if not _col_exists(conn, "directions", col):
                conn.execute(f"ALTER TABLE directions ADD COLUMN {col} {defn}")

    # --- pricing_settings (V2) ---
    if not _table_exists(conn, "pricing_settings"):
        conn.execute("""
            CREATE TABLE pricing_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_by INTEGER DEFAULT NULL REFERENCES users(id)
            )
        """)

    # --- admin_action_audit (V2) ---
    if not _table_exists(conn, "admin_action_audit"):
        conn.execute("""
            CREATE TABLE admin_action_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER NOT NULL REFERENCES users(id),
                target_id INTEGER DEFAULT NULL REFERENCES users(id),
                action TEXT NOT NULL,
                details TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

    # --- Default narx sozlamalari (V2) ---
    if _table_exists(conn, "pricing_settings"):
        defaults = {
            "pro_price_uzs": "99000",
            "pro_price_code": "57000",
            "pro_ai_limit": "100",
            "pro_duration_days": "30",
            "free_ai_limit": "10",
            "free_test_limit": "30",
            "free_smm_access": "0",
            "course_reward_code": "100",
            "ai_cost_per_msg": "200",
            "ai_weekly_price_code": "1",
            "paid_course_code_default": "1",
            "coin_transfer_fee_percent": "5",
            "certificate_exam_fee": "20000",
            "ping_test_free_quota": "10",
            "ping_test_cost_free": "2000",
            "ping_test_pro_quota": "20",
            "ping_test_cost_pro": "1000",
            "ping_test_cyber_pro_quota": "30",
            "ping_test_cost_cyber_pro": "500",
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO pricing_settings (key, value) VALUES (?,?)", (k, v)
            )

    # --- coin_transfers / private_messages (V3) ---
    if not _table_exists(conn, "coin_transfers"):
        conn.execute("""
            CREATE TABLE coin_transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER NOT NULL REFERENCES users(id),
                to_user_id INTEGER NOT NULL REFERENCES users(id),
                amount_sent INTEGER NOT NULL,
                fee_amount INTEGER NOT NULL DEFAULT 0,
                amount_received INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_coin_transfers_from ON coin_transfers(from_user_id)")
        conn.execute("CREATE INDEX idx_coin_transfers_to ON coin_transfers(to_user_id)")

    if not _table_exists(conn, "private_messages"):
        conn.execute("""
            CREATE TABLE private_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL REFERENCES users(id),
                receiver_id INTEGER NOT NULL REFERENCES users(id),
                body TEXT NOT NULL DEFAULT '',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_pm_sender ON private_messages(sender_id)")
        conn.execute("CREATE INDEX idx_pm_receiver ON private_messages(receiver_id)")
        conn.execute("CREATE INDEX idx_pm_pair ON private_messages(sender_id, receiver_id, created_at)")

    # --- treasury_accounts / treasury_fund / treasury_fund_log (V5) ---
    if not _table_exists(conn, "treasury_accounts"):
        conn.execute("""
            CREATE TABLE treasury_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ism TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_login_at TEXT DEFAULT NULL
            )
        """)

    if not _table_exists(conn, "treasury_fund"):
        conn.execute("""
            CREATE TABLE treasury_fund (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                balance INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("INSERT OR IGNORE INTO treasury_fund (id, balance) VALUES (1, 0)")

    if not _table_exists(conn, "treasury_fund_log"):
        conn.execute("""
            CREATE TABLE treasury_fund_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                direction TEXT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                user_id INTEGER DEFAULT NULL REFERENCES users(id),
                treasury_account_id INTEGER DEFAULT NULL REFERENCES treasury_accounts(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_treasury_log_user ON treasury_fund_log(user_id)")
        conn.execute("CREATE INDEX idx_treasury_log_created ON treasury_fund_log(created_at)")

    # --- certificate_applications / direction_exam_attempts (V6) ---
    if not _table_exists(conn, "certificate_applications"):
        conn.execute("""
            CREATE TABLE certificate_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                direction_id INTEGER NOT NULL REFERENCES directions(id),
                custom_id TEXT NOT NULL,
                exam_score INTEGER NOT NULL,
                exam_total INTEGER NOT NULL,
                paid_amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                admin_note TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                reviewed_at TEXT DEFAULT NULL,
                reviewed_by INTEGER DEFAULT NULL REFERENCES users(id),
                certificate_number TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX idx_cert_app_user ON certificate_applications(user_id)")
        conn.execute("CREATE INDEX idx_cert_app_status ON certificate_applications(status)")

    if not _table_exists(conn, "direction_exam_attempts"):
        conn.execute("""
            CREATE TABLE direction_exam_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                direction_id INTEGER NOT NULL REFERENCES directions(id),
                test_score INTEGER NOT NULL,
                test_total INTEGER NOT NULL,
                practice_score INTEGER NOT NULL,
                practice_total INTEGER NOT NULL,
                total_score INTEGER NOT NULL,
                max_total INTEGER NOT NULL,
                passed INTEGER NOT NULL,
                paid_amount INTEGER NOT NULL,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX idx_dir_exam_user ON direction_exam_attempts(user_id)")

    # --- announcements / announcement_views / ping_test_usage (V7) ---
    if not _table_exists(conn, "announcements"):
        conn.execute("""
            CREATE TABLE announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'normal',
                target_plans TEXT NOT NULL DEFAULT 'all',
                is_active INTEGER NOT NULL DEFAULT 1,
                voice_enabled INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER NOT NULL REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT DEFAULT NULL
            )
        """)
        conn.execute("CREATE INDEX idx_announcements_active ON announcements(is_active, created_at)")

    if not _table_exists(conn, "announcement_views"):
        conn.execute("""
            CREATE TABLE announcement_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                announcement_id INTEGER NOT NULL REFERENCES announcements(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                viewed_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(announcement_id, user_id)
            )
        """)

    if not _table_exists(conn, "ping_test_usage"):
        conn.execute("""
            CREATE TABLE ping_test_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                target TEXT NOT NULL,
                response_time_ms INTEGER NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                was_paid INTEGER NOT NULL DEFAULT 0,
                cost_paid INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_ping_usage_user ON ping_test_usage(user_id, created_at)")

    # --- oauth_links (V9) — Google/GitHub orqali ro'yxatdan o'tish/kirish (faqat oddiy foydalanuvchilar) ---
    if not _table_exists(conn, "oauth_links"):
        conn.execute("""
            CREATE TABLE oauth_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                provider TEXT NOT NULL,
                provider_id TEXT NOT NULL,
                email TEXT DEFAULT '',
                name TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(provider, provider_id)
            )
        """)
        conn.execute("CREATE INDEX idx_oauth_links_user ON oauth_links(user_id)")

    # --- email_verifications (V10) — ro'yxatdan o'tishda email tasdiqlash kodi ---
    if not _table_exists(conn, "email_verifications"):
        conn.execute("""
            CREATE TABLE email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                code TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_sent_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX idx_email_verif_user ON email_verifications(user_id)")


    if not _table_exists(conn, "page_access"):
        conn.execute("""
            CREATE TABLE page_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("INSERT OR IGNORE INTO page_access (path, title, is_active) VALUES ('/collection', 'Kolleksiya', 0)")
        conn.execute("INSERT OR IGNORE INTO page_access (path, title, is_active) VALUES ('/smm', 'SMM', 0)")

    conn.commit()
    conn.close()


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_one(sql, args=()):
    cur = get_db().execute(sql, args)
    row = cur.fetchone()
    return dict(row) if row else None


def query_all(sql, args=()):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return [dict(r) for r in rows]


def execute(sql, args=()):
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    return cur.lastrowid


def log_action(user_id, action, details="", ip=""):
    """Har bir muhim amalni xavfsizlik jurnaliga (action_logs) yozadi."""
    try:
        execute(
            "INSERT INTO action_logs (user_id, action, details, ip) VALUES (?,?,?,?)",
            (user_id, action, details, ip),
        )
    except Exception:
        pass  # log yozilmasa ham asosiy funksiya to'xtamasligi kerak
