ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_normalized text;

CREATE TABLE IF NOT EXISTS access_identifiers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  identifier_type text NOT NULL CHECK (identifier_type IN ('telegram_id','username','phone')),
  normalized_value text NOT NULL,
  display_value text NOT NULL,
  decision text NOT NULL CHECK (decision IN ('approved','blocked')),
  linked_telegram_user_id bigint REFERENCES users(telegram_user_id),
  actor_telegram_user_id bigint NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(identifier_type,normalized_value)
);

CREATE TABLE IF NOT EXISTS access_identifier_audit (
  id bigserial PRIMARY KEY,
  identifier_type text NOT NULL,
  normalized_value text NOT NULL,
  action text NOT NULL,
  actor_telegram_user_id bigint NOT NULL,
  linked_telegram_user_id bigint,
  created_at timestamptz NOT NULL DEFAULT now()
);
