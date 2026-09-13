"""Short committed claims; ambiguous sends are quarantined, never blindly retried."""
import os
from .db import connect
from .retention import fresh_for_delivery
from .channel_policy import public_channel_eligible
from .matching import matches

TABLES = {
    'channel': ('channel_outbox_tasks','channel_posts','channel_post_id'),
    'private': ('outbox_tasks','deliveries','delivery_id'),
}


def claim(queue, cutoff):
    tasks, parent, fk = TABLES[queue]
    with connect() as c:
        if c.execute("SELECT 1 FROM telegram_cooldowns WHERE name='bot' AND until_at>now()").fetchone():
            return None
        # A committed processing row means the request may have reached Telegram.
        c.execute(f"""UPDATE {tasks} SET status=CASE WHEN task_type='send' OR %s='private' THEN 'uncertain' ELSE 'failed' END,
            last_error='worker interrupted; delivery outcome requires reconciliation'
            WHERE status='processing' AND locked_at < now()-interval '5 minutes'""",(queue,))
        extra = ''
        args = [cutoff]
        if queue == 'private':
            extra = " AND EXISTS(SELECT 1 FROM users u WHERE u.telegram_user_id=p.telegram_user_id AND u.state='approved')"
            if os.getenv('PRIVATE_DELIVERY_MODE','admin_only') == 'admin_only':
                extra += ' AND p.telegram_user_id=%s'
                args.append(int(os.environ['TELEGRAM_ADMIN_USER_ID']))
            elif os.getenv('PRIVATE_DELIVERY_MODE') != 'all_approved':
                raise ValueError('Invalid PRIVATE_DELIVERY_MODE')
        row = c.execute(f"""SELECT o.*,p.id parent_id,p.chat_id,p.telegram_message_id,
            l.payload,l.first_seen_at {',p.telegram_user_id' if queue=='private' else ''}
            FROM {tasks} o JOIN {parent} p ON p.id=o.{fk} JOIN listings l ON l.id=p.listing_id
            WHERE (o.task_type='mark_removed' OR o.created_at >= %s)
            AND o.status IN ('pending','failed') AND o.next_retry_at <= now() {extra}
            ORDER BY o.created_at FOR UPDATE OF o SKIP LOCKED LIMIT 1""",args).fetchone()
        if not row:
            return None
        reason = None
        if row['task_type'] == 'send':
            if not fresh_for_delivery(row['payload'],row['first_seen_at']):
                reason = 'expired or unavailable freshness evidence'
            elif queue == 'channel' and not public_channel_eligible(row['payload']):
                reason = 'outside monthly Baku apartment channel policy'
            elif queue == 'private':
                filters = c.execute('SELECT basic,additional FROM filters WHERE telegram_user_id=%s AND is_enabled AND deleted_at IS NULL',(row['telegram_user_id'],)).fetchall()
                if row['payload'].get('is_deleted') or not any(matches(row['payload'],f['basic'],f['additional']) for f in filters):
                    reason = 'outside current personal filters'
        if reason:
            c.execute(f"UPDATE {tasks} SET status='cancelled',last_error=%s WHERE id=%s",(reason,row['id']))
            c.execute(f"UPDATE {parent} SET status='failed',last_error=%s,updated_at=now() WHERE id=%s AND telegram_message_id IS NULL",(reason,row['parent_id']))
            return {'cancelled':True}
        if queue == 'private':
            row['language'] = c.execute('SELECT language FROM users WHERE telegram_user_id=%s',(row['telegram_user_id'],)).fetchone()['language']
        c.execute(f"UPDATE {tasks} SET status='processing',locked_at=now(),attempts=attempts+1 WHERE id=%s",(row['id'],))
        row['attempts'] += 1
        row['attempt_id'] = c.execute('INSERT INTO delivery_attempts(queue,task_id) VALUES(%s,%s) RETURNING id',(queue,row['id'])).fetchone()['id']
        return row


def finish(queue, task, status, message_id=None, error=None, due=None):
    tasks, parent, _ = TABLES[queue]
    with connect() as c:
        c.execute(f"""UPDATE {tasks} SET status=%s,last_error=%s,locked_at=NULL,
            next_retry_at=COALESCE(%s,next_retry_at),sent_at=CASE WHEN %s='sent' THEN now() ELSE sent_at END
            WHERE id=%s AND status='processing'""",(status,error,due,status,task['id']))
        c.execute('UPDATE delivery_attempts SET finished_at=now(),outcome=%s,error=%s,telegram_message_id=%s WHERE id=%s',
                  (status,error,message_id,task['attempt_id']))
        if status == 'sent' and task['task_type'] == 'send':
            c.execute(f"UPDATE {parent} SET status='sent',telegram_message_id=%s,sent_at=now(),last_error=NULL,updated_at=now() WHERE id=%s",(message_id,task['parent_id']))
        elif status == 'sent' and queue == 'channel':
            c.execute("UPDATE channel_posts SET status='removed',updated_at=now() WHERE id=%s",(task['parent_id'],))
        elif status != 'sent':
            c.execute(f"UPDATE {parent} SET status='failed',attempts=%s,last_error=%s,next_retry_at=COALESCE(%s,next_retry_at),updated_at=now() WHERE id=%s",(task['attempts'],error,due,task['parent_id']))


def pause_bot(until):
    with connect() as c:
        c.execute("""INSERT INTO telegram_cooldowns(name,until_at) VALUES('bot',%s)
            ON CONFLICT(name) DO UPDATE SET until_at=greatest(telegram_cooldowns.until_at,EXCLUDED.until_at)""",(until,))
