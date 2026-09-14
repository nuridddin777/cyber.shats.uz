"""SHATS CYBER V2 — EDU Blueprint. O'qituvchi, o'quvchi, admin panellari."""
import os, datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, abort, flash
from db import query_one, query_all, execute
from auth import get_current_user
from functools import wraps

edu_bp = Blueprint("edu", __name__, url_prefix="/edu")

def login_required(f):
    @wraps(f)
    def decorated(*a, **kw):
        if not session.get("user_id"): return redirect(url_for("login"))
        return f(*a, **kw)
    return decorated

def _add_edu_coin(uid, amount, reason=""):
    execute("INSERT OR IGNORE INTO edu_coins (user_id, balance) VALUES (?,0)", (uid,))
    execute("UPDATE edu_coins SET balance=balance+? WHERE user_id=?", (amount, uid))
    execute("INSERT INTO edu_coin_transactions (user_id, amount, reason) VALUES (?,?,?)", (uid, amount, reason))

# ===== GEO API =====
@edu_bp.route("/api/districts")
def api_districts():
    rid = request.args.get("region_id", type=int)
    if not rid: return jsonify({"districts": []})
    rows = query_all("SELECT id, name FROM districts WHERE region_id=? ORDER BY name", (rid,))
    return jsonify({"districts": [dict(r) for r in rows]})

@edu_bp.route("/api/schools")
def api_schools():
    did = request.args.get("district_id", type=int)
    st = request.args.get("school_type", "")
    if not did: return jsonify({"schools": []})
    if st:
        rows = query_all("SELECT id, name FROM schools WHERE district_id=? AND school_type=? ORDER BY name", (did, st))
    else:
        rows = query_all("SELECT id, name FROM schools WHERE district_id=? ORDER BY name", (did,))
    return jsonify({"schools": [dict(r) for r in rows]})

@edu_bp.route("/api/classes")
def api_classes():
    sid = request.args.get("school_id", type=int)
    if not sid: return jsonify({"classes": []})
    rows = query_all("SELECT id, name, subject FROM edu_classes WHERE school_id=? AND is_active=1 ORDER BY name", (sid,))
    return jsonify({"classes": [dict(r) for r in rows]})

# ===== O'QUVCHI PANELI =====
@edu_bp.route("/student")
@login_required
def student_dashboard():
    user = get_current_user()
    cls = None
    topics = []
    progress_pct = 0
    if user.get("edu_class_id"):
        cls = query_one("SELECT ec.*, s.name as school_name FROM edu_classes ec LEFT JOIN schools s ON s.id=ec.school_id WHERE ec.id=?", (user["edu_class_id"],))
        if cls:
            topics = query_all("""SELECT t.*, tp.completed FROM edu_topics t
                LEFT JOIN edu_topic_progress tp ON tp.topic_id=t.id AND tp.user_id=?
                WHERE t.class_id=? AND t.is_approved=1 ORDER BY t.topic_order""", (user["id"], cls["id"]))
            if topics:
                done = sum(1 for t in topics if t["completed"])
                progress_pct = round(done / len(topics) * 100)
    coin = query_one("SELECT balance FROM edu_coins WHERE user_id=?", (user["id"],))
    coin_bal = coin["balance"] if coin else 0
    return render_template("edu/student_dashboard.html", user=user, cls=cls, topics=topics,
                           progress_pct=progress_pct, coin_balance=coin_bal)

@edu_bp.route("/student/topic/<int:tid>")
@login_required
def student_topic(tid):
    user = get_current_user()
    topic = query_one("SELECT * FROM edu_topics WHERE id=? AND is_approved=1", (tid,))
    if not topic: abort(404)
    labs = query_all("SELECT * FROM edu_labs WHERE topic_id=? AND is_approved=1", (tid,))
    progress = query_one("SELECT * FROM edu_topic_progress WHERE user_id=? AND topic_id=?", (user["id"], tid))
    submissions = query_all("SELECT * FROM edu_lab_submissions WHERE user_id=? AND lab_id IN (SELECT id FROM edu_labs WHERE topic_id=?)",
                            (user["id"], tid))
    sub_map = {s["lab_id"]: s for s in submissions}
    return render_template("edu/student_topic.html", user=user, topic=topic, labs=labs,
                           progress=progress, sub_map=sub_map)

@edu_bp.route("/student/topic/<int:tid>/complete", methods=["POST"])
@login_required
def complete_topic(tid):
    user = get_current_user()
    topic = query_one("SELECT * FROM edu_topics WHERE id=?", (tid,))
    if not topic: return jsonify({"ok": False})
    existing = query_one("SELECT * FROM edu_topic_progress WHERE user_id=? AND topic_id=?", (user["id"], tid))
    if existing and existing["completed"]:
        return jsonify({"ok": False, "msg": "Allaqachon tugatilgan"})
    if existing:
        execute("UPDATE edu_topic_progress SET completed=1, completed_at=datetime('now') WHERE id=?", (existing["id"],))
    else:
        execute("INSERT INTO edu_topic_progress (user_id, topic_id, completed, completed_at) VALUES (?,?,1,datetime('now'))", (user["id"], tid))
    _add_edu_coin(user["id"], topic["coin_reward"], f"Mavzu: {topic['title']}")
    try:
        execute("UPDATE users SET xp=xp+? WHERE id=?", (topic["xp_reward"], user["id"]))
    except: pass
    return jsonify({"ok": True, "msg": f"+{topic['coin_reward']} coin, +{topic['xp_reward']} XP!"})

@edu_bp.route("/student/lab/<int:lid>/submit", methods=["POST"])
@login_required
def submit_lab(lid):
    user = get_current_user()
    answer = request.form.get("answer", "").strip()
    if not answer: return jsonify({"ok": False, "msg": "Javob yozing"})
    existing = query_one("SELECT id FROM edu_lab_submissions WHERE lab_id=? AND user_id=?", (lid, user["id"]))
    if existing:
        execute("UPDATE edu_lab_submissions SET answer_text=?, status='pending', submitted_at=datetime('now') WHERE id=?",
                (answer, existing["id"]))
    else:
        execute("INSERT INTO edu_lab_submissions (lab_id, user_id, answer_text) VALUES (?,?,?)", (lid, user["id"], answer))
    return jsonify({"ok": True, "msg": "Lab topshirildi!"})

# ===== O'QITUVCHI PANELI =====
@edu_bp.route("/teacher")
@login_required
def teacher_dashboard():
    user = get_current_user()
    classes = query_all("""SELECT ec.*, s.name as school_name,
        (SELECT COUNT(*) FROM edu_class_students WHERE class_id=ec.id) as student_count,
        (SELECT COUNT(*) FROM edu_topics WHERE class_id=ec.id) as topic_count
        FROM edu_classes ec LEFT JOIN schools s ON s.id=ec.school_id
        WHERE ec.teacher_id=? ORDER BY ec.created_at DESC""", (user["id"],))
    pending = query_all("""SELECT ls.*, l.title as lab_title, u.ism, u.familiya
        FROM edu_lab_submissions ls
        JOIN edu_labs l ON l.id=ls.lab_id
        JOIN users u ON u.id=ls.user_id
        JOIN edu_topics t ON t.id=l.topic_id
        JOIN edu_classes ec ON ec.id=t.class_id
        WHERE ec.teacher_id=? AND ls.status='pending'
        ORDER BY ls.submitted_at DESC LIMIT 20""", (user["id"],))
    return render_template("edu/teacher_dashboard.html", user=user, classes=classes, pending=pending)

@edu_bp.route("/teacher/class/create", methods=["GET","POST"])
@login_required
def teacher_create_class():
    user = get_current_user()
    if request.method == "POST":
        name = request.form.get("name","").strip()
        school_id = request.form.get("school_id", type=int)
        subject = request.form.get("subject","")
        if not name or not school_id:
            flash("Sinf nomi va maktab kerak","error")
            return redirect(url_for("edu.teacher_create_class"))
        execute("INSERT INTO edu_classes (name, school_id, teacher_id, subject) VALUES (?,?,?,?)",
                (name, school_id, user["id"], subject))
        flash(f"'{name}' sinfi yaratildi!","success")
        return redirect(url_for("edu.teacher_dashboard"))
    regions = query_all("SELECT id, name FROM regions ORDER BY name")
    return render_template("edu/teacher_create_class.html", user=user, regions=regions)

@edu_bp.route("/teacher/class/<int:cid>")
@login_required
def teacher_class(cid):
    user = get_current_user()
    cls = query_one("SELECT * FROM edu_classes WHERE id=? AND teacher_id=?", (cid, user["id"]))
    if not cls: abort(403)
    topics = query_all("SELECT * FROM edu_topics WHERE class_id=? ORDER BY topic_order", (cid,))
    students = query_all("""SELECT u.id, u.ism, u.familiya, u.email,
        (SELECT COUNT(*) FROM edu_topic_progress WHERE user_id=u.id AND completed=1
         AND topic_id IN (SELECT id FROM edu_topics WHERE class_id=?)) as completed_topics
        FROM edu_class_students ecs JOIN users u ON u.id=ecs.user_id
        WHERE ecs.class_id=?""", (cid, cid))
    return render_template("edu/teacher_class.html", user=user, cls=cls, topics=topics, students=students)

@edu_bp.route("/teacher/class/<int:cid>/topic/add", methods=["POST"])
@login_required
def add_topic(cid):
    user = get_current_user()
    cls = query_one("SELECT id FROM edu_classes WHERE id=? AND teacher_id=?", (cid, user["id"]))
    if not cls: return jsonify({"ok": False})
    title = request.form.get("title","").strip()
    content = request.form.get("content","")
    if not title: return jsonify({"ok": False, "msg": "Mavzu nomi kerak"})
    max_order = query_one("SELECT MAX(topic_order) as m FROM edu_topics WHERE class_id=?", (cid,))
    order = (max_order["m"] or 0) + 1
    execute("INSERT INTO edu_topics (class_id, title, content, topic_order, is_approved) VALUES (?,?,?,?,1)",
            (cid, title, content, order))
    return jsonify({"ok": True, "msg": f"'{title}' mavzusi qo'shildi!"})

@edu_bp.route("/teacher/topic/<int:tid>/lab/add", methods=["POST"])
@login_required
def add_lab(tid):
    title = request.form.get("title","").strip()
    desc = request.form.get("description","")
    if not title: return jsonify({"ok": False, "msg": "Lab nomi kerak"})
    execute("INSERT INTO edu_labs (topic_id, title, description, is_approved) VALUES (?,?,?,1)", (tid, title, desc))
    return jsonify({"ok": True, "msg": "Lab qo'shildi!"})

@edu_bp.route("/teacher/submission/<int:sid>/grade", methods=["POST"])
@login_required
def grade_submission(sid):
    score = request.form.get("score", type=int)
    feedback = request.form.get("feedback","")
    if score is None: return jsonify({"ok": False})
    execute("UPDATE edu_lab_submissions SET score=?, feedback=?, status='graded', graded_at=datetime('now') WHERE id=?",
            (score, feedback, sid))
    sub = query_one("SELECT user_id FROM edu_lab_submissions WHERE id=?", (sid,))
    if sub and score >= 70:
        _add_edu_coin(sub["user_id"], 10, "Lab baholandi")
    return jsonify({"ok": True, "msg": f"Baho qo'yildi: {score}"})

@edu_bp.route("/teacher/class/<int:cid>/student/add", methods=["POST"])
@login_required
def add_student_to_class(cid):
    email = request.form.get("email","").strip()
    if not email: return jsonify({"ok": False, "msg": "Email kerak"})
    student = query_one("SELECT id FROM users WHERE email=?", (email,))
    if not student: return jsonify({"ok": False, "msg": "Foydalanuvchi topilmadi"})
    try:
        execute("INSERT INTO edu_class_students (class_id, user_id) VALUES (?,?)", (cid, student["id"]))
        execute("UPDATE users SET edu_class_id=? WHERE id=?", (cid, student["id"]))
    except: return jsonify({"ok": False, "msg": "Allaqachon qo'shilgan"})
    return jsonify({"ok": True, "msg": "O'quvchi qo'shildi!"})

# ===== EDU COINS =====
@edu_bp.route("/coins")
@login_required
def coins_page():
    user = get_current_user()
    coin = query_one("SELECT balance FROM edu_coins WHERE user_id=?", (user["id"],))
    balance = coin["balance"] if coin else 0
    txns = query_all("SELECT * FROM edu_coin_transactions WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (user["id"],))
    packages = query_all("SELECT * FROM edu_coin_packages WHERE is_active=1")
    return render_template("edu/coins.html", user=user, balance=balance, txns=txns, packages=packages)

# ===== ADMIN =====
@edu_bp.route("/admin/schools")
@login_required
def admin_schools():
    user = get_current_user()
    if user["role"] not in ("admin","super_admin"): abort(403)
    schools = query_all("""SELECT s.*, d.name as district_name, r.name as region_name,
        (SELECT COUNT(*) FROM users WHERE school_id=s.id) as student_count,
        (SELECT COUNT(*) FROM edu_classes WHERE school_id=s.id) as class_count,
        (SELECT tarif FROM school_subscriptions WHERE school_id=s.id AND is_active=1 LIMIT 1) as tarif,
        (SELECT is_active FROM school_subscriptions WHERE school_id=s.id ORDER BY id DESC LIMIT 1) as has_sub
        FROM schools s LEFT JOIN districts d ON d.id=s.district_id
        LEFT JOIN regions r ON r.id=d.region_id ORDER BY r.name, s.name LIMIT 200""")
    regions = query_all("SELECT id, name FROM regions ORDER BY name")
    return render_template("edu/admin_schools.html", user=user, schools=schools, regions=regions)

@edu_bp.route("/admin/school/add", methods=["POST"])
@login_required
def admin_add_school():
    user = get_current_user()
    if user["role"] not in ("admin","super_admin"): return jsonify({"ok": False})
    name = request.form.get("name","").strip()
    school_type = request.form.get("school_type","maktab")
    district_id = request.form.get("district_id", type=int)
    if not name: return jsonify({"ok": False, "msg": "Nom kerak"})
    execute("INSERT INTO schools (name, school_type, district_id) VALUES (?,?,?)", (name, school_type, district_id))
    return jsonify({"ok": True, "msg": f"'{name}' qo'shildi!"})

@edu_bp.route("/admin/school/<int:sid>/activate", methods=["POST"])
@login_required
def admin_activate_tarif(sid):
    user = get_current_user()
    if user["role"] not in ("admin","super_admin"): return jsonify({"ok": False})
    tarif = request.form.get("tarif","oddiy")
    limits = {"oddiy":(100,2),"pro":(300,10),"pro+":(700,50)}
    ms, mt = limits.get(tarif, (100,2))
    execute("UPDATE school_subscriptions SET is_active=0 WHERE school_id=?", (sid,))
    execute("INSERT INTO school_subscriptions (school_id, tarif, max_students, max_teachers) VALUES (?,?,?,?)",
            (sid, tarif, ms, mt))
    return jsonify({"ok": True, "msg": f"'{tarif}' tarifi faollashtirildi!"})

@edu_bp.route("/admin/coins/add", methods=["POST"])
@login_required
def admin_add_coins():
    user = get_current_user()
    if user["role"] not in ("admin","super_admin"): return jsonify({"ok": False})
    uid = request.form.get("user_id", type=int)
    amount = request.form.get("amount", type=int)
    reason = request.form.get("reason","Admin")
    if not uid or not amount: return jsonify({"ok": False})
    _add_edu_coin(uid, amount, reason)
    return jsonify({"ok": True, "msg": f"{amount} coin qo'shildi!"})

@edu_bp.route("/admin/videos")
@login_required
def admin_videos():
    user = get_current_user()
    if user["role"] not in ("admin","super_admin"): abort(403)
    videos = query_all("""SELECT v.*, u.ism as uploader_name FROM edu_videos v
        LEFT JOIN users u ON u.id=v.uploader_id WHERE v.is_approved=0 ORDER BY v.created_at DESC""")
    return render_template("edu/admin_videos.html", user=user, videos=videos)

@edu_bp.route("/admin/videos/<int:vid>/approve", methods=["POST"])
@login_required
def admin_approve_video(vid):
    user = get_current_user()
    if user["role"] not in ("admin","super_admin"): return jsonify({"ok": False})
    execute("UPDATE edu_videos SET is_approved=1 WHERE id=?", (vid,))
    return jsonify({"ok": True})

# Holiday auto-check
def get_active_holiday():
    now = datetime.datetime.now()
    try:
        return query_one("SELECT * FROM holidays WHERE date_month=? AND date_day=? AND is_active=1", (now.month, now.day))
    except: return None

def check_expired_subscriptions():
    try:
        execute("UPDATE school_subscriptions SET is_active=0 WHERE is_active=1 AND expires_at < datetime('now')")
    except: pass
