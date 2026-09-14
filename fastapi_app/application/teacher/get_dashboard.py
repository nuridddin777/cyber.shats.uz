from fastapi_app.domain.teacher.entities import TeacherDashboard
from fastapi_app.domain.teacher.repository import TeacherRepository


class NotTeacherError(Exception):
    pass


def get_dashboard(repo: TeacherRepository, user_id: int) -> TeacherDashboard:
    if not repo.is_teacher(user_id):
        raise NotTeacherError()
    return TeacherDashboard(
        is_teacher=True,
        my_groups=repo.list_my_groups(user_id),
        my_channels=repo.list_my_channels(user_id),
    )
