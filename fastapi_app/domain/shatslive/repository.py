from typing import Protocol

from fastapi_app.domain.shatslive.entities import LiveStream


class ShatsLiveRepository(Protocol):
    def list_streams(self, limit: int) -> list[LiveStream]: ...
    def get_user_plan(self, user_id: int) -> str | None: ...
