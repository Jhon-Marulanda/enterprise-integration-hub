from sqlalchemy.orm import Session

from models import Order, OrderItem
from schemas import OrderSchema
from sqlalchemy.exc import IntegrityError


def create_order(db: Session, order_data: OrderSchema) -> Order:
    order = Order(
        external_order_id=order_data.external_order_id,
        customer_document_number=order_data.customer.document_number,
        customer_name=order_data.customer.name,
        customer_email=order_data.customer.email,
        currency=order_data.currency,
        status="pending",
    )

    for item_data in order_data.items:
        item = OrderItem(
            product_code=item_data.product_code,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
        )
        order.items.append(item)

    try:
        db.add(order)
        db.commit()
        db.refresh(order)
    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(getattr(exc, "orig", None), "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "orders_external_order_id_key":
            raise DuplicateOrderError(
                "An order with this external ID already exists."
            ) from exc

        raise
    except Exception:
        db.rollback()
        raise

    return order

class DuplicateOrderError(Exception):
    pass