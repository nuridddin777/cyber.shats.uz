from fastapi_app.domain.ids.entities import PremiumId
from fastapi_app.domain.ids.repository import IdsRepository


def list_marketplace(repo: IdsRepository) -> list[PremiumId]:
    return repo.list_marketplace()
