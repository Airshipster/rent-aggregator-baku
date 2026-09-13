"""Retire sends without destroying their identity, history or removal updates."""
from datetime import datetime, timedelta, timezone
from .db import connect
from src.utils import image_datetime, parse_dt


def fresh_for_delivery(payload, first_seen_at=None, now=None):
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    dates = [parse_dt(payload.get('updated_at')), image_datetime(payload.get('first_image_url'))]
    dates = [d for d in dates if d is not None]
    if first_seen_at is not None:
        dates.append(first_seen_at)
    # Source updated time/photo age remain proxies, not verified creation time.
    return bool(dates) and all(d.tzinfo is not None and cutoff <= d <= now + timedelta(minutes=5) for d in dates)


def expire_pending():
    counts = {}
    with connect() as conn:
        for queue, parent, fk in [('outbox_tasks','deliveries','delivery_id'),
                                  ('channel_outbox_tasks','channel_posts','channel_post_id')]:
            rows = conn.execute(f"""UPDATE {queue} o SET status='cancelled',last_error='expired: older than seven days'
                FROM {parent} p,listings l
                WHERE o.{fk}=p.id AND p.listing_id=l.id AND o.task_type='send'
                AND o.status IN ('pending','failed')
                AND (o.created_at < now()-interval '7 days' OR l.first_seen_at < now()-interval '7 days')
                RETURNING p.id""").fetchall()
            for row in rows:
                conn.execute(f"UPDATE {parent} SET status='failed',last_error='expired: older than seven days',updated_at=now() WHERE id=%s AND telegram_message_id IS NULL",(row['id'],))
            counts[queue] = len(rows)
    return counts


def compact_retired():
    """Remove old cleanup history, retaining minimal delivery deduplication keys."""
    counts = {}
    with connect() as c:
        c.execute("SELECT pg_advisory_xact_lock(hashtext('rent-retention'))")
        for queue, parent, fk, name in [('outbox_tasks','deliveries','delivery_id','private'),
                                       ('channel_outbox_tasks','channel_posts','channel_post_id','channel')]:
            rows = c.execute(f"""SELECT p.id FROM {parent} p JOIN listings l ON l.id=p.listing_id
                JOIN {queue} o ON o.{fk}=p.id AND o.task_type='mark_removed'
                JOIN message_cleanup_receipts r ON r.parent_id=p.id AND r.queue=%s
                WHERE l.status='removed' AND o.status='sent' AND r.completed_at < now()-interval '14 days'
                AND NOT EXISTS(SELECT 1 FROM {queue} t WHERE t.{fk}=p.id
                    AND t.status IN ('pending','processing','failed','uncertain'))
                ORDER BY r.completed_at FOR UPDATE OF p SKIP LOCKED LIMIT 250""",(name,)).fetchall()
            for row in rows:
                c.execute(f'DELETE FROM delivery_attempts WHERE queue=%s AND task_id IN (SELECT id FROM {queue} WHERE {fk}=%s)',(name,row['id']))
                c.execute(f'DELETE FROM {queue} WHERE {fk}=%s',(row['id'],))
                c.execute(f"UPDATE {parent} SET telegram_message_id=NULL,sent_at=NULL,last_error=NULL,attempts=0,updated_at=now() WHERE id=%s",(row['id'],))
                c.execute('DELETE FROM message_cleanup_receipts WHERE queue=%s AND parent_id=%s',(name,row['id']))
            counts[name] = len(rows)
        # Keep the root ID so a bumped/reintroduced listing cannot be delivered as new.
        rows = c.execute("""UPDATE listings l SET payload=jsonb_build_object('listing_id',source_listing_id,
            'source',source,'is_deleted',true,'compacted',true)
            WHERE status='removed' AND removed_at < now()-interval '14 days'
            AND NOT payload @> '{"compacted":true}'::jsonb
            AND NOT EXISTS(SELECT 1 FROM deliveries d WHERE d.listing_id=l.id AND d.telegram_message_id IS NOT NULL)
            AND NOT EXISTS(SELECT 1 FROM channel_posts p WHERE p.listing_id=l.id AND p.telegram_message_id IS NOT NULL)
            AND NOT EXISTS(SELECT 1 FROM deliveries d JOIN outbox_tasks o ON o.delivery_id=d.id WHERE d.listing_id=l.id AND o.status IN ('pending','processing','failed','uncertain'))
            AND NOT EXISTS(SELECT 1 FROM channel_posts p JOIN channel_outbox_tasks o ON o.channel_post_id=p.id WHERE p.listing_id=l.id AND o.status IN ('pending','processing','failed','uncertain'))
            RETURNING id""").fetchall()
        counts['payloads'] = len(rows)
        # Accepted spool payloads are transport copies, not the canonical listing.
        c.execute("DELETE FROM collector_spool WHERE accepted_at < now()-interval '14 days'")
    return counts


if __name__ == '__main__':
    print(expire_pending())
