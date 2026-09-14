from typing import Protocol

from fastapi_app.domain.bejik.entities import BadgeStats


class BejikRepository(Protocol):
    def get_stats(self, user_id: int) -> BadgeStats: ...
