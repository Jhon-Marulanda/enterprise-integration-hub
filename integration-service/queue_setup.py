
import pika

from rabbitmq import get_rabbitmq_connection


MAIN_QUEUE = "orders"
RETRY_QUEUE = "orders.retry"
DLQ_QUEUE = "orders.dlq"
DLX_EXCHANGE = "orders.dlx"

RETRY_DELAY_MS = 10_000


def main() -> None:
    connection = get_rabbitmq_connection()

    try:
        channel = connection.channel()

        # Exchange used by the policy applied to the main queue.
        channel.exchange_declare(
            exchange=DLX_EXCHANGE,
            exchange_type="direct",
            durable=True,
        )

        # Queue for permanently failed messages.
        channel.queue_declare(
            queue=DLQ_QUEUE,
            durable=True,
        )

        channel.queue_bind(
            queue=DLQ_QUEUE,
            exchange=DLX_EXCHANGE,
            routing_key=DLQ_QUEUE,
        )

        # Retry queue: expired messages return to the main queue.
        channel.queue_declare(
            queue=RETRY_QUEUE,
            durable=True,
            arguments={
                "x-message-ttl": RETRY_DELAY_MS,
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": MAIN_QUEUE,
            },
        )

        print("RabbitMQ queues configured successfully.")
        print(f"Main queue: {MAIN_QUEUE} (configured using policy)")
        print(f"Retry queue: {RETRY_QUEUE}")
        print(f"Dead-letter queue: {DLQ_QUEUE}")

    finally:
        if connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
