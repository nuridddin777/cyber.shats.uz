from fastapi_app.domain.certificates.entities import Certificate
from fastapi_app.domain.certificates.repository import CertificatesRepository


def list_for_user(repo: CertificatesRepository, user_id: int) -> list[Certificate]:
    return repo.list_for_user(user_id)
