ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS pinned_menu_message_id bigint;

UPDATE users
SET pinned_menu_message_id=menu_message_id,
    menu_message_id=NULL
WHERE pinned_menu_message_id IS NULL AND menu_message_id IS NOT NULL;
