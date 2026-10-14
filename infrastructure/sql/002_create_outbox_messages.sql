-- Messages waiting to be published to RabbitMQ
CREATE TABLE outbox_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    order_id BIGINT NOT NULL
        REFERENCES orders(id) ON DELETE RESTRICT,

    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'published')),

    attempts INTEGER NOT NULL DEFAULT 0
        CHECK (attempts >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_outbox_messages_pending
    ON outbox_messages(created_at, id)
    WHERE status = 'pending';
