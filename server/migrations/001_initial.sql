CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS listings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  source_listing_id text NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','removed')),
  first_seen_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  removed_at timestamptz,
  UNIQUE (source, source_listing_id)
);
CREATE TABLE IF NOT EXISTS users (
  telegram_user_id bigint PRIMARY KEY,
  chat_id bigint NOT NULL,
  first_name text,
  username text,
  language text NOT NULL DEFAULT 'ru' CHECK (language IN ('ru','az','en')),
  state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','approved','rejected','deactivated')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deactivated_at timestamptz
);
CREATE TABLE IF NOT EXISTS user_access_audit (
  id bigserial PRIMARY KEY,
  telegram_user_id bigint NOT NULL REFERENCES users(telegram_user_id),
  action text NOT NULL,
  actor_telegram_user_id bigint,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_user_id bigint NOT NULL REFERENCES users(telegram_user_id),
  provider text NOT NULL,
  provider_transaction_id text NOT NULL,
  amount_minor bigint NOT NULL,
  currency text NOT NULL,
  status text NOT NULL,
  access_granted_until timestamptz,
  provider_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(provider, provider_transaction_id)
);
CREATE TABLE IF NOT EXISTS filters (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_user_id bigint NOT NULL REFERENCES users(telegram_user_id),
  name text NOT NULL DEFAULT 'Основной фильтр',
  is_enabled boolean NOT NULL DEFAULT true,
  basic jsonb NOT NULL DEFAULT '{}'::jsonb,
  additional jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz
);
CREATE TABLE IF NOT EXISTS deliveries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id uuid NOT NULL REFERENCES listings(id),
  telegram_user_id bigint NOT NULL REFERENCES users(telegram_user_id),
  chat_id bigint NOT NULL,
  telegram_message_id bigint,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','failed')),
  attempts integer NOT NULL DEFAULT 0,
  next_retry_at timestamptz NOT NULL DEFAULT now(),
  sent_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(listing_id, telegram_user_id)
);
CREATE TABLE IF NOT EXISTS outbox_tasks (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  delivery_id uuid NOT NULL REFERENCES deliveries(id),
  task_type text NOT NULL CHECK (task_type IN ('send','mark_removed')),
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','sent','failed')),
  attempts integer NOT NULL DEFAULT 0,
  next_retry_at timestamptz NOT NULL DEFAULT now(),
  locked_at timestamptz,
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  sent_at timestamptz,
  UNIQUE(delivery_id, task_type)
);
CREATE TABLE IF NOT EXISTS ingest_requests (
  idempotency_key text PRIMARY KEY,
  body_sha256 text NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS telegram_updates (
  update_id bigint PRIMARY KEY,
  received_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS outbox_due_idx ON outbox_tasks(status, next_retry_at);
CREATE INDEX IF NOT EXISTS filters_user_idx ON filters(telegram_user_id) WHERE deleted_at IS NULL;
