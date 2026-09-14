from typing import Protocol

from fastapi_app.domain.securityzone.entities import SecurityZoneOverview


class SecurityZoneRepository(Protocol):
    def get_overview(self, user_id: int) -> SecurityZoneOverview: ...
    def get_user_plan(self, user_id: int) -> str | None: ...
