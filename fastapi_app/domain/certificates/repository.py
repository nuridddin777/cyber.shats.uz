from typing import Protocol

from fastapi_app.domain.certificates.entities import Certificate


class CertificatesRepository(Protocol):
    def list_for_user(self, user_id: int) -> list[Certificate]: ...
