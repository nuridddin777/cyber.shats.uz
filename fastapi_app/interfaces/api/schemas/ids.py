from pydantic import BaseModel


class PremiumIdResponse(BaseModel):
    id: int
    custom_id: str
    id_type: str
    base_price: int
    status: str
    owner_user_id: int | None
