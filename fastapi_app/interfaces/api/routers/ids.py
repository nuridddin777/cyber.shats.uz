"""
Fourth FastAPI slice: premium ID marketplace, READ-ONLY, public (mirrors
ids.py's get_premium_ids_list() — no auth in the original either). Buying/
selling/auctioning IDs stays in the existing ids.py for now — that's a
much deeper write surface (auctions, reservations, treasury revenue).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.ids.list_marketplace import list_marketplace
from fastapi_app.infrastructure.db.repositories.ids_repository import SqlAlchemyIdsRepository
from fastapi_app.interfaces.api.deps import get_db_session
from fastapi_app.interfaces.api.schemas.ids import PremiumIdResponse

router = APIRouter(prefix="/api/v2/ids", tags=["ids"])


@router.get("/marketplace", response_model=list[PremiumIdResponse])
def marketplace(db: Session = Depends(get_db_session)):
    repo = SqlAlchemyIdsRepository(db)
    return [PremiumIdResponse(**i.__dict__) for i in list_marketplace(repo)]
