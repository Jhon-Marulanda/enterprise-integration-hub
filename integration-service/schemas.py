
from decimal import Decimal

from pydantic import BaseModel, Field


class CustomerSchema(BaseModel):
    document_number: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: str


class OrderItemSchema(BaseModel):
    product_code: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)


class OrderSchema(BaseModel):
    external_order_id: str = Field(min_length=1)
    customer: CustomerSchema
    items: list[OrderItemSchema] = Field(min_length=1)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
