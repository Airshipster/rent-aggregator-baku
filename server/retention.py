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


if __name__ == '__main__':
    print(expire_pending())
