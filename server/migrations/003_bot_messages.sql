CREATE TABLE IF NOT EXISTS bot_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_user_id bigint REFERENCES users(telegram_user_id),
  chat_id bigint NOT NULL,
  telegram_message_id bigint NOT NULL,
  kind text NOT NULL,
  status text NOT NULL DEFAULT 'sent' CHECK (status IN ('sent','deleted','failed')),
  created_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  UNIQUE(chat_id, telegram_message_id)
);
