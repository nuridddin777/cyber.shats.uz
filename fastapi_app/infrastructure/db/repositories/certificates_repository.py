from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi_app.domain.certificates.entities import Certificate
from fastapi_app.infrastructure.db.models.certificate import CertificateModel
from fastapi_app.infrastructure.db.models.course import CourseModel


class SqlAlchemyCertificatesRepository:
    def __init__(self, db: Session):
        self._db = db

    def list_for_user(self, user_id: int) -> list[Certificate]:
        rows = self._db.execute(
            select(CertificateModel, CourseModel.title)
            .join(CourseModel, CourseModel.id == CertificateModel.course_id)
            .where(CertificateModel.user_id == user_id)
            .order_by(CertificateModel.issued_at.desc())
        ).all()
        return [
            Certificate(
                id=cert.id, course_id=cert.course_id, course_title=title,
                cert_code=cert.cert_code, issued_at=cert.issued_at,
            )
            for cert, title in rows
        ]
