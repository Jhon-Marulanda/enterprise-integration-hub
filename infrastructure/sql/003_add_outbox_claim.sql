-- Add temporary claims to coordinate concurrent outbox publishers.
ALTER TABLE outbox_messages
    ADD COLUMN claimed_until TIMESTAMPTZ NULL,
    ADD COLUMN claim_token UUID NULL;
