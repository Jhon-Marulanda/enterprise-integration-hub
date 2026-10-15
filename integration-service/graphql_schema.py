from datetime import datetime

import strawberry
from sqlalchemy import select

from database import SessionLocal
from models import Order


@strawberry.type
class OrderType:
    external_order_id: str
    status: str
    currency: str
    created_at: datetime
    updated_at: datetime


@strawberry.type
class Query:
    @strawberry.field
    def order(self, external_order_id: str) -> OrderType | None:
        """Retrieve an order by its external identifier."""

        with SessionLocal() as db:
            order = db.scalar(
                select(Order).where(
                    Order.external_order_id == external_order_id
                )
            )

            if order is None:
                return None

            return OrderType(
                external_order_id=order.external_order_id,
                status=order.status,
                currency=order.currency,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )


schema = strawberry.Schema(query=Query)
