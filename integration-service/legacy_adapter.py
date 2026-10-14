
import logging
import os

from models import Order


logger = logging.getLogger(__name__)


def submit_order_to_legacy(order: Order) -> str:
    """
    Simulate a SOAP request to a legacy system.

    A specific order can be configured to fail for retry testing.
    """

    logger.info(
        "SOAP request simulated for order: %s",
        order.external_order_id,
    )

    # Fail only when the order ID matches the configured test ID.
    failure_order_id = os.getenv("LEGACY_SIMULATE_FAILURE_FOR")

    if failure_order_id == order.external_order_id:
        logger.error(
            "Simulated SOAP failure for order: %s",
            order.external_order_id,
        )
        raise RuntimeError("Simulated legacy SOAP service failure.")

    # Simulate a successful legacy response.
    legacy_reference = f"LEGACY-{order.external_order_id}"

    logger.info(
        "SOAP response simulated: order accepted, reference=%s",
        legacy_reference,
    )

    return legacy_reference
