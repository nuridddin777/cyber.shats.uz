# ============================================================
# CYBER SHATS — Admin Tashkilotlar va Maxsus Imtiyozlar (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import admin_required
from db import query_one, query_all, execute
import datetime

admintashkilot_bp = Blueprint("admintashkilot_bp", __name__)


@admintashkilot_bp.route("/admin/tashkilotlar", methods=["GET", "POST"])
@admin_required
def admin_organizations():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_org":
            org_key = request.form.get("org_key")
            execute(
                "UPDATE organizations SET name=?, description=?, stats_members=?, stats_projects=?, "
                "stats_years=?, updated_at=datetime('now') WHERE org_key=?",
                (request.form.get("name"), request.form.get("description"),
                 request.form.get("stats_members", 0), request.form.get("stats_projects", 0),
                 request.form.get("stats_years", 0), org_key)
            )
            flash("Tashkilot ma'lumotlari yangilandi.", "success")
        elif action == "add_post":
            execute("INSERT INTO organization_posts (org_key, title, content) VALUES (?,?,?)",
                    (request.form.get("org_key"), request.form.get("title"), request.form.get("content")))
            flash("E'lon qo'shildi.", "success")
        elif action == "resolve_request":
            req_id = request.form.get("request_id")
            new_status = request.form.get("new_status")
            execute("UPDATE organization_requests SET status=? WHERE id=?", (new_status, req_id))
            flash("So'rov holati yangilandi.", "success")
        return redirect(url_for("admin_organizations"))

    orgs = query_all("SELECT * FROM organizations")
    requests_list = query_all(
        """SELECT r.*, u.ism, u.familiya, u.custom_id FROM organization_requests r
           JOIN users u ON u.id = r.user_id ORDER BY r.created_at DESC LIMIT 50"""
    )
    return render_template("admin_organizations.html", orgs=orgs, requests_list=requests_list)


@admintashkilot_bp.route("/admin/maxsus-imtiyozlar", methods=["GET", "POST"])
@admin_required
def admin_hacker_perks():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            execute("INSERT INTO hacker_perks (title, description, link, icon) VALUES (?,?,?,?)",
                    (request.form.get("title"), request.form.get("description"),
                     request.form.get("link", ""), request.form.get("icon", "gift")))
            flash("Imtiyoz qo'shildi.", "success")
        elif action == "delete":
            execute("DELETE FROM hacker_perks WHERE id=?", (request.form.get("perk_id"),))
            flash("Imtiyoz o'chirildi.", "success")
        return redirect(url_for(".admin_hacker_perks"))
    perks = query_all("SELECT * FROM hacker_perks ORDER BY order_index, id")
    return render_template("admin_hacker_perks.html", perks=perks)
