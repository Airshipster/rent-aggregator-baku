ALTER TABLE outbox_tasks DROP CONSTRAINT IF EXISTS outbox_tasks_status_check;
ALTER TABLE outbox_tasks ADD CONSTRAINT outbox_tasks_status_check
 CHECK (status IN ('pending','processing','sent','failed','dead_letter','cancelled','uncertain'));
ALTER TABLE channel_outbox_tasks DROP CONSTRAINT IF EXISTS channel_outbox_tasks_status_check;
ALTER TABLE channel_outbox_tasks ADD CONSTRAINT channel_outbox_tasks_status_check
 CHECK (status IN ('pending','processing','sent','failed','dead_letter','cancelled','uncertain'));
CREATE TABLE IF NOT EXISTS service_health (
 name text PRIMARY KEY, heartbeat_at timestamptz NOT NULL DEFAULT now(),
 last_success_at timestamptz, last_error text, details jsonb NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS delivery_attempts (
 id bigserial PRIMARY KEY, queue text NOT NULL, task_id uuid NOT NULL,
 started_at timestamptz NOT NULL DEFAULT now(), finished_at timestamptz,
 outcome text NOT NULL DEFAULT 'started', error text, telegram_message_id bigint
);
CREATE INDEX IF NOT EXISTS delivery_attempt_task ON delivery_attempts(queue, task_id);
CREATE TABLE IF NOT EXISTS telegram_cooldowns (
 name text PRIMARY KEY, until_at timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS collector_candidates (
 source_listing_id text PRIMARY KEY, discovered_at timestamptz NOT NULL DEFAULT now(),
 source_updated_at timestamptz, channel_candidate boolean NOT NULL DEFAULT true,
 status text NOT NULL DEFAULT 'pending', attempts integer NOT NULL DEFAULT 0,
 next_retry_at timestamptz NOT NULL DEFAULT now(), fetched_at timestamptz, last_error text
);
CREATE TABLE IF NOT EXISTS collector_spool (
 id uuid PRIMARY KEY DEFAULT gen_random_uuid(), source_listing_id text NOT NULL,
 payload jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), accepted_at timestamptz
);
