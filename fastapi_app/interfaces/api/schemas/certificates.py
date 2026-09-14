from pydantic import BaseModel


class CertificateResponse(BaseModel):
    id: int
    course_id: int
    course_title: str
    cert_code: str
    issued_at: str
