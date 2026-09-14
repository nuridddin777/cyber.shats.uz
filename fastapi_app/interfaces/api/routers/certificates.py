"""
Fifth FastAPI slice: a user's own issued certificates, READ-ONLY.
Mirrors the query used in app.py's dashboard route. Certificate exam
applications/review workflow stays in certificates.py for now.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.application.certificates.list_for_user import list_for_user
from fastapi_app.infrastructure.db.repositories.certificates_repository import SqlAlchemyCertificatesRepository
from fastapi_app.interfaces.api.deps import get_current_user_id, get_db_session
from fastapi_app.interfaces.api.schemas.certificates import CertificateResponse

router = APIRouter(prefix="/api/v2/certificates", tags=["certificates"])


@router.get("", response_model=list[CertificateResponse])
def my_certificates(user_id: int = Depends(get_current_user_id), db: Session = Depends(get_db_session)):
    repo = SqlAlchemyCertificatesRepository(db)
    return [CertificateResponse(**c.__dict__) for c in list_for_user(repo, user_id)]
