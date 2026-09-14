# ============================================================
# PLATFORM INNOVATIONS — Maxsus (Pro) versiya 20 ta xususiyat
# ============================================================
# Kirish nazorati mavjud kod bazasidagi naqsh bilan bir xil:
#   user.plan in ('pro','cyber_pro','vip') YOKI
#   user.role in ('admin','super_admin','mentor')

from db import query_all, query_one, execute


PLAN_HIERARCHY = {"free": 0, "pro": 1, "cyber_pro": 2, "vip": 3}


class InnovationAccessError(Exception):
    pass


def _user_meets_plan(user: dict, required_plan: str) -> bool:
    if user.get("role") in ("admin", "super_admin", "mentor"):
        return True
    user_level = PLAN_HIERARCHY.get(user.get("plan"), 0)
    required_level = PLAN_HIERARCHY.get(required_plan, 1)
    return user_level >= required_level


def list_features_for_user(user: dict):
    """Foydalanuvchiga ko'rinadigan (ochiq/yopiq holati bilan) barcha 20 xususiyat."""
    rows = query_all(
        "SELECT * FROM platform_innovation_features WHERE is_active=1 ORDER BY sort_order"
    )
    result = []
    for r in rows:
        r = dict(r)
        r["unlocked"] = _user_meets_plan(user, r["required_plan"])
        result.append(r)
    return result


def check_access_or_raise(user: dict, feature_key: str):
    feature = query_one("SELECT * FROM platform_innovation_features WHERE feature_key=? AND is_active=1", (feature_key,))
    if not feature:
        raise InnovationAccessError("Bunday xususiyat topilmadi")
    if not _user_meets_plan(user, feature["required_plan"]):
        raise InnovationAccessError(
            f"Bu xususiyat uchun kamida '{feature['required_plan']}' tarif kerak"
        )
    return feature


def start_or_get_progress(user_id: int, feature_key: str):
    feature = query_one("SELECT * FROM platform_innovation_features WHERE feature_key=?", (feature_key,))
    if not feature:
        raise InnovationAccessError("Bunday xususiyat topilmadi")

    progress = query_one(
        "SELECT * FROM platform_innovation_progress WHERE feature_id=? AND user_id=?",
        (feature["id"], user_id))
    if progress:
        return progress

    execute(
        "INSERT INTO platform_innovation_progress (feature_id, user_id, status) VALUES (?,?, 'started')",
        (feature["id"], user_id))
    return query_one(
        "SELECT * FROM platform_innovation_progress WHERE feature_id=? AND user_id=?",
        (feature["id"], user_id))


def update_progress(user_id: int, feature_key: str, status: str = None, data: dict = None, score: float = None):
    import json
    feature = query_one("SELECT id FROM platform_innovation_features WHERE feature_key=?", (feature_key,))
    if not feature:
        raise InnovationAccessError("Bunday xususiyat topilmadi")

    fields, params = [], []
    if status:
        fields.append("status=?"); params.append(status)
    if data is not None:
        fields.append("data_json=?"); params.append(json.dumps(data, ensure_ascii=False))
    if score is not None:
        fields.append("score=?"); params.append(score)
    fields.append("updated_at=datetime('now')")

    params += [feature["id"], user_id]
    execute(f"UPDATE platform_innovation_progress SET {', '.join(fields)} WHERE feature_id=? AND user_id=?", tuple(params))
