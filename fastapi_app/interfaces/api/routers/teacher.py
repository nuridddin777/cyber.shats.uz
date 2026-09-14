"""
Twenty-fifth FastAPI slice: teacher dashboard, READ-ONLY. Mirrors
teacher_routes.py's teacher_dashboard() route (owned groups + channels),
including its teacher_required gate (is_teacher flag or admin/super_admin
role). Creating groups/channels/courses stays on the legacy Flask side.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi_app.application.teacher.get_dashboard import NotTeacherError, get_dashboard
from fastapi_app.infrastructure.db.repositories.teacher_repository import SqlAlchemyTeacherRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.teacher import (
    TeacherChannelResponse, TeacherDashboardResponse, TeacherGroupResponse,
)

router = APIRouter(prefix="/api/v2/teacher", tags=["teacher"])


@router.get("", response_model=TeacherDashboardResponse)
def teacher(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyTeacherRepository(db)
    try:
        dashboard = get_dashboard(repo, user_id)
    except NotTeacherError:
        raise HTTPException(status_code=403, detail="Bu bo'lim faqat tasdiqlangan o'qituvchilar uchun.")
    return TeacherDashboardResponse(
        is_teacher=dashboard.is_teacher,
        my_groups=[TeacherGroupResponse(**g.__dict__) for g in dashboard.my_groups],
        my_channels=[TeacherChannelResponse(**c.__dict__) for c in dashboard.my_channels],
    )
