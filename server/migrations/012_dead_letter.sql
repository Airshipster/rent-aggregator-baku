-- Keep parent delivery records and all technical evidence; never delete failures.
ALTER TABLE outbox_tasks DROP CONSTRAINT IF EXISTS outbox_tasks_status_check;
ALTER TABLE outbox_tasks ADD CONSTRAINT outbox_tasks_status_check
  CHECK (status IN ('pending','processing','sent','failed','dead_letter'));
ALTER TABLE channel_outbox_tasks DROP CONSTRAINT IF EXISTS channel_outbox_tasks_status_check;
ALTER TABLE channel_outbox_tasks ADD CONSTRAINT channel_outbox_tasks_status_check
  CHECK (status IN ('pending','processing','sent','failed','dead_letter'));
