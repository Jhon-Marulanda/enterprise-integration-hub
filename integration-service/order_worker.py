
import json
import logging

import pika
from sqlalchemy import select

from database import SessionLocal
from legacy_adapter import submit_order_to_legacy
from message_publisher import QUEUE_NAME
from models import Order
from rabbitmq import get_rabbitmq_connection


RETRY_QUEUE = "orders.retry"
DLQ_QUEUE = "orders.dlq"
MAX_RETRIES = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


class LegacyIntegrationError(Exception):
    """Raised when the legacy integration fails."""


def update_order_status(order_data: dict, new_status: str) -> None:
    """Update an order status in PostgreSQL."""

    with SessionLocal() as db:
        order = db.scalar(
            select(Order).where(
                Order.id == order_data["order_id"],
                Order.external_order_id == order_data["external_order_id"],
            )
        )

        if order is None:
            raise ValueError(
                f"Order not found: {order_data['external_order_id']}"
            )

        order.status = new_status
        db.commit()


def process_order(order_data: dict) -> None:
    """Process an order through the simulated legacy integration."""

    order_id = order_data.get("order_id")
    external_order_id = order_data.get("external_order_id")

    if (
        not isinstance(order_id, int)
        or isinstance(order_id, bool)
        or not isinstance(external_order_id, str)
        or not external_order_id
    ):
        raise ValueError("The message contains invalid order identifiers.")

    with SessionLocal() as db:
        order = db.scalar(
            select(Order).where(
                Order.id == order_id,
                Order.external_order_id == external_order_id,
            )
        )

        if order is None:
            raise ValueError(f"Order not found: {external_order_id}")

        if order.status == "succeeded":
            logger.info("Order already completed: %s", external_order_id)
            return

        order.status = "processing"
        db.commit()

        logger.info(
            "Order status updated: %s -> processing",
            external_order_id,
        )

        try:
            legacy_reference = submit_order_to_legacy(order)

        except Exception as exc:
            logger.exception(
                "Legacy integration failed for order: %s",
                external_order_id,
            )

            # Keep the order in processing while retries remain.
            raise LegacyIntegrationError(
                f"Legacy integration failed for {external_order_id}"
            ) from exc

        order.status = "succeeded"
        db.commit()

        logger.info(
            "Order completed: %s -> succeeded; legacy_reference=%s",
            external_order_id,
            legacy_reference,
        )


def publish_retry(channel, order_data: dict, retry_count: int) -> None:
    """Publish a persistent message to the retry queue."""

    retry_data = {
        **order_data,
        "retry_count": retry_count,
    }

    channel.basic_publish(
        exchange="",
        routing_key=RETRY_QUEUE,
        body=json.dumps(retry_data),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
        mandatory=True,
    )


def main() -> None:
    connection = get_rabbitmq_connection()
    channel = connection.channel()

    channel.queue_declare(
        queue=QUEUE_NAME,
        durable=True,
    )

    channel.basic_qos(prefetch_count=1)

    # Require broker confirmation when publishing retry messages.
    channel.confirm_delivery()

    def callback(ch, method, properties, body):
        order_data = None

        try:
            order_data = json.loads(body.decode("utf-8"))

            if not isinstance(order_data, dict):
                raise ValueError("The message must contain a JSON object.")

            retry_count = order_data.get("retry_count", 0)

            if (
                not isinstance(retry_count, int)
                or isinstance(retry_count, bool)
                or retry_count < 0
            ):
                raise ValueError("The retry_count value is invalid.")

            process_order(order_data)

        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            logger.error("Invalid order message: %s", exc)

            # The main queue's DLX policy routes rejected messages to orders.dlq.
            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )
            return

        except LegacyIntegrationError:
            try:
                if retry_count < MAX_RETRIES:
                    next_retry = retry_count + 1

                    publish_retry(ch, order_data, next_retry)

                    logger.warning(
                        "Retry scheduled for %s: attempt %s of %s",
                        order_data["external_order_id"],
                        next_retry + 1,
                        MAX_RETRIES + 1,
                    )

                    # Acknowledge only after RabbitMQ confirms the retry publish.
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    return

                update_order_status(order_data, "failed")

                logger.error(
                    "Retries exhausted for order: %s",
                    order_data["external_order_id"],
                )

                # Route the final failed message to the DLQ.
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=False,
                )
                return

            except Exception:
                logger.exception("Could not schedule or finalize retry")

                # Keep the original message available if retry publishing fails.
                if ch.is_open:
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True,
                    )
                return

        except Exception:
            logger.exception("Unexpected error processing order")

            ch.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True,
            )
            return

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback,
        auto_ack=False,
    )

    logger.info("Worker listening on queue '%s'...", QUEUE_NAME)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Worker stopped by user.")
    finally:
        if channel.is_open:
            channel.close()
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
