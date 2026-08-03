CREATE TABLE IF NOT EXISTS channel_posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id uuid NOT NULL UNIQUE REFERENCES listings(id),
  chat_id bigint NOT NULL,
  telegram_message_id bigint,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','failed')),
  attempts integer NOT NULL DEFAULT 0,
  next_retry_at timestamptz NOT NULL DEFAULT now(),
  sent_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS channel_outbox_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  channel_post_id uuid NOT NULL REFERENCES channel_posts(id),
  task_type text NOT NULL CHECK (task_type IN ('send','mark_removed')),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','sent','failed')),
  attempts integer NOT NULL DEFAULT 0,
  next_retry_at timestamptz NOT NULL DEFAULT now(),
  locked_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  sent_at timestamptz,
  UNIQUE(channel_post_id, task_type)
);
CREATE INDEX IF NOT EXISTS channel_outbox_due_idx ON channel_outbox_tasks(status, next_retry_at);
