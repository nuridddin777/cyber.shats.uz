"""
SHATS CYBER V2 — Virtual Olam (Virtual World) Blueprint.
3D virtual dunyo: xonalar, avatarlar, inventar, do'kon, questlar, chat.
"""
import os
import json
import datetime
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify, abort, flash
from db import query_one, query_all, execute
from auth import get_current_user
from functools import wraps

virtual_bp = Blueprint("virtual", __name__, url_prefix="/virtual")

# ============================================================
# VIRTUAL OLAM — HOZIRCHA YOPIQ (keyingi versiyada qo'shiladi)
# Kod o'zi o'chirilmaydi — faqat kirish yopiladi, shunda keyingi
# versiyada bitta qatorni o'chirish bilan qayta yoqish mumkin bo'ladi.
# ============================================================
VIRTUAL_WORLD_ENABLED = False


@virtual_bp.before_request
def _virtual_world_closed_gate():
    if VIRTUAL_WORLD_ENABLED:
        return None
    if request.path.startswith("/virtual/api/") or request.path.startswith("/virtual/admin"):
        return jsonify(success=False, error="Virtual olam hozircha yopiq."), 503
    return render_template("virtual_world_closed.html"), 200


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ==================== AVATAR HELPERS ====================

def get_or_create_avatar(user_id):
    """Foydalanuvchi avatarini olish yoki yangisini yaratish."""
    avatar = query_one("SELECT * FROM vw_avatars WHERE user_id=?", (user_id,))
    if not avatar:
        user = query_one("SELECT ism, familiya FROM users WHERE id=?", (user_id,))
        nickname = f"{user['ism']}_{user['familiya']}" if user else f"User_{user_id}"
        execute("""INSERT INTO vw_avatars (user_id, nickname) VALUES (?,?)""", (user_id, nickname))
        avatar = query_one("SELECT * FROM vw_avatars WHERE user_id=?", (user_id,))
    return avatar


def add_avatar_xp(user_id, xp_amount):
    """Avatar XP qo'shish va level tekshirish."""
    avatar = get_or_create_avatar(user_id)
    new_xp = avatar["xp"] + xp_amount
    new_level = avatar["level"]
    # Har 100 XP = 1 level
    while new_xp >= new_level * 100:
        new_xp -= new_level * 100
        new_level += 1
    execute("UPDATE vw_avatars SET xp=?, level=? WHERE user_id=?", (new_xp, new_level, user_id))


def add_avatar_coins(user_id, amount, description=""):
    """Virtual coin qo'shish/ayirish."""
    execute("UPDATE vw_avatars SET coins = coins + ? WHERE user_id=?", (amount, user_id))
    execute("INSERT INTO vw_transactions (user_id, transaction_type, amount, description) VALUES (?,?,?,?)",
            (user_id, "earn" if amount > 0 else "spend", amount, description))


# ==================== MAIN PAGES ====================

@virtual_bp.route("/")
@login_required
def world_home():
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    rooms = query_all("SELECT * FROM vw_rooms WHERE is_active=1 ORDER BY id")
    # Online foydalanuvchilar
    online_count = query_one("""SELECT COUNT(*) as c FROM vw_avatars
                                WHERE is_online=1 AND last_seen > datetime('now','-5 minutes')""")
    # Aktiv questlar
    active_quests = query_all("""SELECT q.*, qp.status, qp.progress FROM vw_quests q
                                  LEFT JOIN vw_quest_progress qp ON qp.quest_id=q.id AND qp.user_id=?
                                  WHERE q.is_active=1 AND (qp.status IS NULL OR qp.status='active')
                                  LIMIT 5""", (user["id"],))
    return render_template("virtual/home.html", user=user, avatar=avatar, rooms=rooms,
                           online_count=online_count["c"] if online_count else 0,
                           active_quests=active_quests)


@virtual_bp.route("/room/<slug>")
@login_required
def enter_room(slug):
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    room = query_one("SELECT * FROM vw_rooms WHERE slug=? AND is_active=1", (slug,))
    if not room:
        flash("Xona topilmadi.", "error")
        return redirect(url_for("virtual.world_home"))

    # Level tekshirish
    if room["required_level"] > avatar["level"]:
        flash(f"Bu xona uchun {room['required_level']}-level kerak. Sizda {avatar['level']}-level.", "error")
        return redirect(url_for("virtual.world_home"))

    # Avatarni shu xonaga joylashtirish
    execute("UPDATE vw_avatars SET current_room_id=?, is_online=1, last_seen=datetime('now') WHERE user_id=?",
            (room["id"], user["id"]))

    # Xonadagi boshqa foydalanuvchilar
    room_users = query_all("""SELECT a.*, u.ism, u.familiya, u.plan FROM vw_avatars a
                              JOIN users u ON u.id=a.user_id
                              WHERE a.current_room_id=? AND a.is_online=1
                              AND a.last_seen > datetime('now','-5 minutes')
                              AND a.user_id != ?
                              LIMIT 30""", (room["id"], user["id"]))

    # Xona obyektlari
    objects = query_all("SELECT * FROM vw_room_objects WHERE room_id=? AND is_active=1", (room["id"],))

    # Oxirgi chat xabarlari
    messages = query_all("""SELECT vc.*, u.ism, a.nickname, a.outfit_color FROM vw_chat vc
                            JOIN users u ON u.id=vc.user_id
                            LEFT JOIN vw_avatars a ON a.user_id=vc.user_id
                            WHERE vc.room_id=?
                            ORDER BY vc.created_at DESC LIMIT 50""", (room["id"],))
    messages = list(reversed(messages))

    return render_template("virtual/room.html", user=user, avatar=avatar, room=room,
                           room_users=room_users, objects=objects, messages=messages)


# ==================== AVATAR ====================

@virtual_bp.route("/avatar")
@login_required
def avatar_page():
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    inventory = query_all("""SELECT vi.*, vit.name as item_name, vit.item_type, vit.rarity,
                              vit.icon, vit.color as item_color
                              FROM vw_inventory vi
                              JOIN vw_items vit ON vit.id=vi.item_id
                              WHERE vi.user_id=?
                              ORDER BY vi.is_equipped DESC, vi.acquired_at DESC""", (user["id"],))
    return render_template("virtual/avatar.html", user=user, avatar=avatar, inventory=inventory)


@virtual_bp.route("/avatar/update", methods=["POST"])
@login_required
def avatar_update():
    user = get_current_user()
    fields = ["nickname", "skin_color", "hair_style", "hair_color",
              "outfit", "outfit_color", "accessory"]
    updates = []
    params = []
    for f in fields:
        val = request.form.get(f)
        if val:
            updates.append(f"{f}=?")
            params.append(val)
    if updates:
        params.append(user["id"])
        execute(f"UPDATE vw_avatars SET {','.join(updates)} WHERE user_id=?", tuple(params))
    return jsonify({"ok": True, "msg": "Avatar yangilandi!"})


# ==================== DO'KON (SHOP) ====================

@virtual_bp.route("/shop")
@login_required
def shop():
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    items = query_all("SELECT * FROM vw_items WHERE is_active=1 ORDER BY rarity DESC, price_coins ASC")
    # Foydalanuvchida bor buyumlar
    owned = set()
    rows = query_all("SELECT item_id FROM vw_inventory WHERE user_id=?", (user["id"],))
    for r in rows:
        owned.add(r["item_id"])
    return render_template("virtual/shop.html", user=user, avatar=avatar, items=items, owned=owned)


@virtual_bp.route("/shop/buy/<int:item_id>", methods=["POST"])
@login_required
def shop_buy(item_id):
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    item = query_one("SELECT * FROM vw_items WHERE id=? AND is_active=1", (item_id,))
    if not item:
        return jsonify({"ok": False, "msg": "Buyum topilmadi"})

    # Tekshirish — allaqachon bormi
    existing = query_one("SELECT id FROM vw_inventory WHERE user_id=? AND item_id=?", (user["id"], item_id))
    if existing:
        return jsonify({"ok": False, "msg": "Bu buyum sizda allaqachon bor"})

    # MUHIM (tuzatilgan race condition): balans avval ALOHIDA o'qilib, keyin
    # ALOHIDA UPDATE bilan kamaytirilardi (add_avatar_coins() hech qanday
    # tekshiruvsiz kamaytiradi) — ikkita deyarli bir vaqtdagi xarid bitta
    # balansdan ikkalasi ham yechishi mumkin edi. Endi BITTA atomik
    # UPDATE...WHERE bilan.
    updated = query_one(
        "UPDATE vw_avatars SET coins = coins - ? WHERE user_id=? AND coins >= ? RETURNING coins",
        (item["price_coins"], user["id"], item["price_coins"])
    )
    if not updated:
        return jsonify({"ok": False, "msg": f"Yetarli coin yo'q. Kerak: {item['price_coins']}, Sizda: {avatar['coins']}"})

    # Sotib olish
    execute("INSERT INTO vw_transactions (user_id, transaction_type, amount, description) VALUES (?,?,?,?)",
            (user["id"], "spend", -item["price_coins"], f"Do'kondan: {item['name']}"))
    execute("INSERT INTO vw_inventory (user_id, item_id) VALUES (?,?)", (user["id"], item_id))
    add_avatar_xp(user["id"], 5)

    return jsonify({"ok": True, "msg": f"'{item['name']}' sotib olindi! 🎉"})


# ==================== INVENTAR ====================

@virtual_bp.route("/inventory/equip/<int:inv_id>", methods=["POST"])
@login_required
def equip_item(inv_id):
    user = get_current_user()
    inv = query_one("SELECT * FROM vw_inventory WHERE id=? AND user_id=?", (inv_id, user["id"]))
    if not inv:
        return jsonify({"ok": False, "msg": "Buyum topilmadi"})

    item = query_one("SELECT item_type FROM vw_items WHERE id=?", (inv["item_id"],))
    # Avvalgi shu turdagi buyumni yechish
    if item:
        execute("""UPDATE vw_inventory SET is_equipped=0
                   WHERE user_id=? AND item_id IN (SELECT id FROM vw_items WHERE item_type=?)""",
                (user["id"], item["item_type"]))

    execute("UPDATE vw_inventory SET is_equipped=1 WHERE id=?", (inv_id,))
    return jsonify({"ok": True, "msg": "Buyum kiyildi!"})


# ==================== CHAT ====================

@virtual_bp.route("/api/chat/send", methods=["POST"])
@login_required
def chat_send():
    user = get_current_user()
    room_id = request.form.get("room_id", type=int)
    message = request.form.get("message", "").strip()
    if not room_id or not message or len(message) > 500:
        return jsonify({"ok": False, "msg": "Xabar noto'g'ri"})

    execute("INSERT INTO vw_chat (room_id, user_id, message) VALUES (?,?,?)",
            (room_id, user["id"], message))
    # XP
    add_avatar_xp(user["id"], 1)
    # Online yangilash
    execute("UPDATE vw_avatars SET is_online=1, last_seen=datetime('now') WHERE user_id=?", (user["id"],))

    return jsonify({"ok": True})


@virtual_bp.route("/api/chat/messages/<int:room_id>")
@login_required
def chat_messages(room_id):
    after_id = request.args.get("after", 0, type=int)
    messages = query_all("""SELECT vc.id, vc.message, vc.created_at, u.ism, a.nickname, a.outfit_color
                            FROM vw_chat vc
                            JOIN users u ON u.id=vc.user_id
                            LEFT JOIN vw_avatars a ON a.user_id=vc.user_id
                            WHERE vc.room_id=? AND vc.id > ?
                            ORDER BY vc.created_at DESC LIMIT 20""", (room_id, after_id))
    return jsonify({"ok": True, "messages": [dict(m) for m in reversed(messages)]})


# ==================== DO'STLAR ====================

@virtual_bp.route("/friends")
@login_required
def friends_page():
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    friends = query_all("""SELECT vf.*, u.ism, u.familiya, a.nickname, a.level, a.is_online, a.current_room_id,
                            r.name as room_name
                            FROM vw_friends vf
                            JOIN users u ON u.id = CASE WHEN vf.user_id=? THEN vf.friend_id ELSE vf.user_id END
                            LEFT JOIN vw_avatars a ON a.user_id = u.id
                            LEFT JOIN vw_rooms r ON r.id = a.current_room_id
                            WHERE (vf.user_id=? OR vf.friend_id=?) AND vf.status='accepted'""",
                         (user["id"], user["id"], user["id"]))
    pending = query_all("""SELECT vf.*, u.ism, u.familiya, a.nickname FROM vw_friends vf
                           JOIN users u ON u.id=vf.user_id
                           LEFT JOIN vw_avatars a ON a.user_id=vf.user_id
                           WHERE vf.friend_id=? AND vf.status='pending'""", (user["id"],))
    return render_template("virtual/friends.html", user=user, avatar=avatar, friends=friends, pending=pending)


@virtual_bp.route("/friends/add/<int:target_id>", methods=["POST"])
@login_required
def add_friend(target_id):
    user = get_current_user()
    if target_id == user["id"]:
        return jsonify({"ok": False, "msg": "O'zingizga so'rov yubora olmaysiz"})
    existing = query_one("""SELECT id FROM vw_friends
                            WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)""",
                         (user["id"], target_id, target_id, user["id"]))
    if existing:
        return jsonify({"ok": False, "msg": "So'rov allaqachon yuborilgan"})
    execute("INSERT INTO vw_friends (user_id, friend_id) VALUES (?,?)", (user["id"], target_id))
    return jsonify({"ok": True, "msg": "Do'stlik so'rovi yuborildi!"})


@virtual_bp.route("/friends/accept/<int:req_id>", methods=["POST"])
@login_required
def accept_friend(req_id):
    user = get_current_user()
    req = query_one("SELECT * FROM vw_friends WHERE id=? AND friend_id=? AND status='pending'",
                    (req_id, user["id"]))
    if not req:
        return jsonify({"ok": False, "msg": "So'rov topilmadi"})
    execute("UPDATE vw_friends SET status='accepted' WHERE id=?", (req_id,))
    add_avatar_xp(user["id"], 5)
    add_avatar_xp(req["user_id"], 5)
    return jsonify({"ok": True, "msg": "Do'st qo'shildi! 🤝"})


# ==================== QUESTLAR ====================

@virtual_bp.route("/quests")
@login_required
def quests_page():
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    quests = query_all("""SELECT q.*, qp.status, qp.progress, qp.completed_at FROM vw_quests q
                          LEFT JOIN vw_quest_progress qp ON qp.quest_id=q.id AND qp.user_id=?
                          WHERE q.is_active=1
                          ORDER BY CASE WHEN qp.status='completed' THEN 1 ELSE 0 END, q.id""",
                       (user["id"],))
    return render_template("virtual/quests.html", user=user, avatar=avatar, quests=quests)


@virtual_bp.route("/quests/complete/<int:quest_id>", methods=["POST"])
@login_required
def complete_quest(quest_id):
    user = get_current_user()
    quest = query_one("SELECT * FROM vw_quests WHERE id=? AND is_active=1", (quest_id,))
    if not quest:
        return jsonify({"ok": False, "msg": "Quest topilmadi"})
    progress = query_one("SELECT * FROM vw_quest_progress WHERE user_id=? AND quest_id=?",
                         (user["id"], quest_id))
    if progress and progress["status"] == "completed":
        return jsonify({"ok": False, "msg": "Bu quest allaqachon bajarilgan"})

    # Tugatish
    if progress:
        execute("UPDATE vw_quest_progress SET status='completed', completed_at=datetime('now') WHERE id=?",
                (progress["id"],))
    else:
        execute("""INSERT INTO vw_quest_progress (user_id, quest_id, status, completed_at)
                   VALUES (?,?,'completed',datetime('now'))""", (user["id"], quest_id))

    # Mukofot
    add_avatar_coins(user["id"], quest["reward_coins"], f"Quest: {quest['title']}")
    add_avatar_xp(user["id"], quest["reward_xp"])
    if quest["reward_item_id"]:
        existing = query_one("SELECT id FROM vw_inventory WHERE user_id=? AND item_id=?",
                             (user["id"], quest["reward_item_id"]))
        if not existing:
            execute("INSERT INTO vw_inventory (user_id, item_id) VALUES (?,?)",
                    (user["id"], quest["reward_item_id"]))

    return jsonify({"ok": True, "msg": f"Quest bajarildi! +{quest['reward_coins']} coin, +{quest['reward_xp']} XP 🎉"})


# ==================== LEADERBOARD ====================

@virtual_bp.route("/leaderboard")
@login_required
def leaderboard():
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    top_users = query_all("""SELECT a.*, u.ism, u.familiya, u.plan FROM vw_avatars a
                             JOIN users u ON u.id=a.user_id
                             ORDER BY a.level DESC, a.xp DESC LIMIT 50""")
    return render_template("virtual/leaderboard.html", user=user, avatar=avatar, top_users=top_users)


# ==================== API — Real-time data ====================

@virtual_bp.route("/api/room/<int:room_id>/users")
@login_required
def api_room_users(room_id):
    """Xonadagi onlayn foydalanuvchilar ro'yxati."""
    user = get_current_user()
    # Heartbeat
    execute("UPDATE vw_avatars SET is_online=1, last_seen=datetime('now') WHERE user_id=?", (user["id"],))
    users = query_all("""SELECT a.user_id, a.nickname, a.level, a.outfit_color, a.skin_color,
                          a.position_x, a.position_y, a.position_z, u.ism, u.plan
                          FROM vw_avatars a JOIN users u ON u.id=a.user_id
                          WHERE a.current_room_id=? AND a.is_online=1
                          AND a.last_seen > datetime('now','-2 minutes')""", (room_id,))
    return jsonify({"ok": True, "users": [dict(u) for u in users]})


@virtual_bp.route("/api/avatar/move", methods=["POST"])
@login_required
def api_avatar_move():
    """Avatar pozitsiyasini yangilash."""
    user = get_current_user()
    x = request.form.get("x", type=float, default=0)
    y = request.form.get("y", type=float, default=0)
    z = request.form.get("z", type=float, default=0)
    execute("UPDATE vw_avatars SET position_x=?, position_y=?, position_z=?, last_seen=datetime('now') WHERE user_id=?",
            (x, y, z, user["id"]))
    return jsonify({"ok": True})


@virtual_bp.route("/api/stats")
@login_required
def api_stats():
    user = get_current_user()
    avatar = get_or_create_avatar(user["id"])
    total_users = query_one("SELECT COUNT(*) as c FROM vw_avatars")
    online = query_one("SELECT COUNT(*) as c FROM vw_avatars WHERE is_online=1 AND last_seen > datetime('now','-5 minutes')")
    return jsonify({
        "level": avatar["level"],
        "xp": avatar["xp"],
        "coins": avatar["coins"],
        "total_users": total_users["c"] if total_users else 0,
        "online": online["c"] if online else 0,
    })


# ==================== ADMIN: Virtual Olam Nazorati ====================

@virtual_bp.route("/admin")
@login_required
def admin_virtual():
    user = get_current_user()
    if user["role"] not in ("admin", "super_admin"):
        abort(403)
    rooms = query_all("SELECT * FROM vw_rooms ORDER BY id")
    items = query_all("SELECT * FROM vw_items ORDER BY id")
    quests = query_all("SELECT * FROM vw_quests ORDER BY id")
    stats = {
        "total_avatars": query_one("SELECT COUNT(*) as c FROM vw_avatars")["c"],
        "online_now": query_one("SELECT COUNT(*) as c FROM vw_avatars WHERE is_online=1 AND last_seen > datetime('now','-5 minutes')")["c"],
        "total_items": len(items),
        "total_rooms": len(rooms),
    }
    return render_template("virtual/admin.html", user=user, rooms=rooms, items=items, quests=quests, stats=stats)


@virtual_bp.route("/admin/room/add", methods=["POST"])
@login_required
def admin_add_room():
    user = get_current_user()
    if user["role"] not in ("admin", "super_admin"):
        return jsonify({"ok": False})
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower().replace(" ", "_")
    desc = request.form.get("description", "")
    room_type = request.form.get("room_type", "public")
    theme = request.form.get("theme", "cyber_city")
    if not name or not slug:
        return jsonify({"ok": False, "msg": "Nom va slug kerak"})
    execute("""INSERT INTO vw_rooms (name, slug, description, room_type, theme, created_by)
               VALUES (?,?,?,?,?,?)""", (name, slug, desc, room_type, theme, user["id"]))
    return jsonify({"ok": True, "msg": f"'{name}' xonasi yaratildi!"})


@virtual_bp.route("/admin/item/add", methods=["POST"])
@login_required
def admin_add_item():
    user = get_current_user()
    if user["role"] not in ("admin", "super_admin"):
        return jsonify({"ok": False})
    name = request.form.get("name", "").strip()
    item_type = request.form.get("item_type", "accessory")
    rarity = request.form.get("rarity", "common")
    price = request.form.get("price_coins", type=int, default=10)
    color = request.form.get("color", "#FFFFFF")
    desc = request.form.get("description", "")
    if not name:
        return jsonify({"ok": False, "msg": "Nom kerak"})
    execute("""INSERT INTO vw_items (name, item_type, rarity, description, color, price_coins)
               VALUES (?,?,?,?,?,?)""", (name, item_type, rarity, desc, color, price))
    return jsonify({"ok": True, "msg": f"'{name}' buyumi qo'shildi!"})
