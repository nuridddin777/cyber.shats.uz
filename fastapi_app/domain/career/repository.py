from typing import Protocol

from fastapi_app.domain.career.entities import JobListing


class CareerRepository(Protocol):
    def list_open(self, viewer_user_id: int) -> list[JobListing]: ...
    def get_user_plan(self, user_id: int) -> str | None: ...
