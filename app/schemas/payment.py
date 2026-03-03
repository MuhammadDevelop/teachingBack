from pydantic import BaseModel


class PaymentCreate(BaseModel):
    course_id: int
    provider: str = "payme"  # payme or click


class PaymentResponse(BaseModel):
    id: int
    amount: int
    provider: str
    status: str
    payment_url: str | None = None

    model_config = {"from_attributes": True}
