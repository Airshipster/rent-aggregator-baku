CREATE TABLE IF NOT EXISTS message_cleanup_receipts (
 queue text NOT NULL CHECK (queue IN ('channel','private')),
 parent_id uuid NOT NULL,
 completed_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(queue,parent_id)
);
CREATE INDEX IF NOT EXISTS message_cleanup_due ON message_cleanup_receipts(completed_at);
