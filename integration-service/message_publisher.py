
import json

import pika

from rabbitmq import get_rabbitmq_connection


QUEUE_NAME = "orders"


def publish_order(order_data: dict) -> None:
    """Publish an order message to RabbitMQ."""

    connection = get_rabbitmq_connection()

    try:
        channel = connection.channel()

        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True,
        )

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(order_data, default=str),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
        )
    finally:
        if connection.is_open:
            connection.close()
