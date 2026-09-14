from fastapi_app.domain.enrollments.entities import Enrollment
from fastapi_app.domain.enrollments.repository import EnrollmentsRepository


def list_for_user(repo: EnrollmentsRepository, user_id: int) -> list[Enrollment]:
    return repo.list_for_user(user_id)
