ALTER TABLE users ADD COLUMN IF NOT EXISTS menu_message_id bigint;
ALTER TABLE users ADD COLUMN IF NOT EXISTS menu_pinned_at timestamptz;
