from typing import Protocol

from fastapi_app.domain.enrollments.entities import Enrollment


class EnrollmentsRepository(Protocol):
    def list_for_user(self, user_id: int) -> list[Enrollment]: ...
