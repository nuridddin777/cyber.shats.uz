from typing import Protocol

from fastapi_app.domain.ids.entities import PremiumId


class IdsRepository(Protocol):
    def list_marketplace(self) -> list[PremiumId]: ...
