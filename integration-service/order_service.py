
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Order, OrderItem, OutboxMessage
from schemas import OrderSchema


class DuplicateOrderError(Exception):
    pass


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
        # Save the order and its items within the current transaction.
        db.add(order)
        db.flush()

        # Build the event that will eventually be published to RabbitMQ.
        outbox_message = OutboxMessage(
            order_id=order.id,
            event_type="order.created",
            payload={
                "order_id": order.id,
                "external_order_id": order.external_order_id,
            },
        )
        db.add(outbox_message)

        # Commit both the order and the outbox message atomically.
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
