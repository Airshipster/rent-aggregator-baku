UPDATE bot_messages AS message
SET kind='pinned_launcher'
FROM users AS account
WHERE message.telegram_user_id=account.telegram_user_id
  AND message.telegram_message_id=account.pinned_menu_message_id
  AND message.status='sent';
