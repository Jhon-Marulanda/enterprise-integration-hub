from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID

from database import Base



class Order(Base):
    __tablename__ = "orders"

    __table_args__ = (
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="orders_currency_check"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="orders_status_check",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    external_order_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )

    customer_document_number: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    customer_name: Mapped[str] = mapped_column(String(150), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(254), nullable=False)

    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default="pending"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    __table_args__ = (
        CheckConstraint("quantity > 0", name="order_items_quantity_check"),
        CheckConstraint("unit_price > 0", name="order_items_unit_price_check"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )

    product_code: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped[Order] = relationship(back_populates="items")


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'published')",
            name="outbox_messages_status_check",
        ),
        CheckConstraint(
            "attempts >= 0",
            name="outbox_messages_attempts_check",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), primary_key=True
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )

    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )

    payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending"
    )

    attempts: Mapped[int] = mapped_column(
        nullable=False, server_default="0"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    published_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    claimed_until: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    claim_token: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        nullable=True,
    )
