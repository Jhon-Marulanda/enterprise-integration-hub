import json
import logging
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pika
from sqlalchemy import or_, select, update

from database import SessionLocal
from models import OutboxMessage
from message_publisher import QUEUE_NAME
from rabbitmq import get_rabbitmq_connection


POLL_INTERVAL_SECONDS = 3
BATCH_SIZE = 10
CLAIM_DURATION_SECONDS = 60

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def claim_pending_messages() -> list[tuple[int, str, dict]]:
    """Atomically reserve a batch of pending messages."""
    claim_token = str(uuid4())
    claimed_messages = []
    claim_expiration = datetime.now(timezone.utc) + timedelta(
        seconds=CLAIM_DURATION_SECONDS
    )

    with SessionLocal() as db:
        message_ids = db.scalars(
            select(OutboxMessage.id)
            .where(
                OutboxMessage.status == "pending",
                or_(
                    OutboxMessage.claimed_until.is_(None),
                    OutboxMessage.claimed_until < datetime.now(timezone.utc),
                ),
            )
            .order_by(OutboxMessage.id)
            .limit(BATCH_SIZE)
            .with_for_update(skip_locked=True)
        ).all()

        if not message_ids:
            return []

        db.execute(
            update(OutboxMessage)
            .where(
                OutboxMessage.id.in_(message_ids),
                OutboxMessage.status == "pending",
            )
            .values(
                claim_token=claim_token,
                claimed_until=claim_expiration,
            )
        )

        db.commit()

        messages = db.scalars(
            select(OutboxMessage)
            .where(
                OutboxMessage.id.in_(message_ids),
                OutboxMessage.claim_token == claim_token,
            )
            .order_by(OutboxMessage.id)
        ).all()

        for message in messages:
            claimed_messages.append(
                (message.id, claim_token, dict(message.payload))
            )

    return claimed_messages


def publish_pending_messages() -> int:
    """Publish claimed messages and persist each outcome."""
    messages = claim_pending_messages()

    if not messages:
        return 0

    try:
        connection = get_rabbitmq_connection()
    except Exception:
        logger.exception("Could not connect to RabbitMQ.")
        release_claims(messages)
        return 0

    published_count = 0

    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.confirm_delivery()

        for message_id, claim_token, payload in messages:
            # Count this attempt before trying to publish.
            with SessionLocal() as db:
                result = db.execute(
                    update(OutboxMessage)
                    .where(
                        OutboxMessage.id == message_id,
                        OutboxMessage.status == "pending",
                        OutboxMessage.claim_token == claim_token,
                    )
                    .values(attempts=OutboxMessage.attempts + 1)
                )
                db.commit()

                if result.rowcount != 1:
                    logger.warning(
                        "Outbox message %s is no longer owned by this publisher.",
                        message_id,
                    )
                    continue

            try:
                channel.basic_publish(
                    exchange="",
                    routing_key=QUEUE_NAME,
                    body=json.dumps(payload),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type="application/json",
                    ),
                    mandatory=True,
                )

                with SessionLocal() as db:
                    result = db.execute(
                        update(OutboxMessage)
                        .where(
                            OutboxMessage.id == message_id,
                            OutboxMessage.status == "pending",
                            OutboxMessage.claim_token == claim_token,
                        )
                        .values(
                            status="published",
                            published_at=datetime.now(timezone.utc),
                            claim_token=None,
                            claimed_until=None,
                        )
                    )
                    db.commit()

                    if result.rowcount == 1:
                        published_count += 1
                        logger.info(
                            "Outbox message %s published for order %s",
                            message_id,
                            payload.get("external_order_id"),
                        )
                    else:
                        logger.warning(
                            "Message %s was confirmed by RabbitMQ, but its "
                            "claim was lost before the database update.",
                            message_id,
                        )

            except Exception:
                logger.exception(
                    "Failed to publish outbox message %s",
                    message_id,
                )
                release_claims([(message_id, claim_token, payload)])

    finally:
        if connection.is_open:
            connection.close()

    return published_count


def release_claims(messages: list[tuple[int, str, dict]]) -> None:
    """Release claims after a known failure, allowing an immediate retry."""
    with SessionLocal() as db:
        for message_id, claim_token, _payload in messages:
            db.execute(
                update(OutboxMessage)
                .where(
                    OutboxMessage.id == message_id,
                    OutboxMessage.status == "pending",
                    OutboxMessage.claim_token == claim_token,
                )
                .values(
                    claim_token=None,
                    claimed_until=None,
                )
            )
        db.commit()


def main() -> None:
    logger.info("Outbox publisher started.")

    while True:
        try:
            count = publish_pending_messages()

            if count:
                logger.info("Published %s outbox message(s).", count)

        except Exception:
            logger.exception("Outbox publisher iteration failed.")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
