from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from fastapi_app.infrastructure.db.base import Base


class CertificateModel(Base):
    __tablename__ = "certificates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    course_id: Mapped[int] = mapped_column(BigInteger)
    cert_code: Mapped[str] = mapped_column(Text)
    issued_at: Mapped[str] = mapped_column(Text)
