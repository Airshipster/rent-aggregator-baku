ALTER TABLE users ADD COLUMN IF NOT EXISTS language_selected boolean NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS wizard jsonb NOT NULL DEFAULT '{}'::jsonb;
UPDATE users SET language_selected=true WHERE state='approved' AND telegram_user_id=106662708;
