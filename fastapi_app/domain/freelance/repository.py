from typing import Protocol

from fastapi_app.domain.freelance.entities import FreelanceGig


class FreelanceRepository(Protocol):
    def list_open(self, limit: int) -> list[FreelanceGig]: ...
    def get_user_plan(self, user_id: int) -> str | None: ...
