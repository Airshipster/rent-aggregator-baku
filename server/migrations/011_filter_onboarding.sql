ALTER TABLE users ADD COLUMN IF NOT EXISTS filter_onboarding_completed boolean NOT NULL DEFAULT false;
UPDATE users SET filter_onboarding_completed=true
WHERE EXISTS (SELECT 1 FROM filters WHERE filters.telegram_user_id=users.telegram_user_id AND filters.deleted_at IS NULL);
