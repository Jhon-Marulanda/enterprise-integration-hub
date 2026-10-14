
import os

import pika
from dotenv import load_dotenv


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def get_rabbitmq_connection() -> pika.BlockingConnection:
    """Create a connection to the RabbitMQ broker."""

    credentials = pika.PlainCredentials(
        username=os.environ["RABBITMQ_USER"],
        password=os.environ["RABBITMQ_PASSWORD"],
    )

    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        virtual_host="/",
        credentials=credentials,
        heartbeat=60,
        connection_attempts=3,
        retry_delay=2,
    )

    return pika.BlockingConnection(parameters)
