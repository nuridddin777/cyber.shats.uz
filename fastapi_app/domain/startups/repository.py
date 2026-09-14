from typing import Protocol

from fastapi_app.domain.startups.entities import Startup


class StartupsRepository(Protocol):
    def list_approved(self, viewer_user_id: int, limit: int) -> list[Startup]: ...
