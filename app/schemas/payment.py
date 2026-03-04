from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PaymentCreate(BaseModel):
    module_id: int


class PaymentResponse(BaseModel):
    id: int
    module_id: int
    amount: int
    status: str
    check_image_url: str | None = None
    admin_comment: str | None = None
    created_at: datetime | None = None
    reviewed_at: datetime | None = None

    class Config:
        from_attributes = True


class PaymentCardInfo(BaseModel):
    card_number: str
    card_holder: str
    card_expiry: str


class PaymentReview(BaseModel):
    status: str  # approved or rejected
    admin_comment: str | None = None
