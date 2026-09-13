"""Run inside the app container via stdin; read-only, aggregate output only."""
import hashlib
import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


QUERIES = {
    "clock": "SELECT now(), current_setting('TimeZone') AS timezone",
    "last_stages": """SELECT
      (SELECT max(received_at) FROM ingest_requests) AS ingest,
      (SELECT max(first_seen_at) FROM listings) AS discovered,
      (SELECT max(last_seen_at) FROM listings) AS listing_update,
      (SELECT max(received_at) FROM telegram_updates) AS webhook,
      (SELECT max(created_at) FROM channel_outbox_tasks) AS channel_queued,
      (SELECT max(sent_at) FROM channel_posts) AS channel_sent,
      (SELECT max(sent_at) FROM deliveries) AS private_sent""",
    "channel_queue": "SELECT task_type,status,count(*),min(created_at) AS oldest,max(created_at) AS newest,max(attempts) AS attempts FROM channel_outbox_tasks GROUP BY 1,2",
    "private_queue": "SELECT task_type,status,count(*),min(created_at) AS oldest,max(created_at) AS newest,max(attempts) AS attempts FROM outbox_tasks GROUP BY 1,2",
    "private_errors": "SELECT split_part(last_error,':',1) AS error_type,count(*),max(attempts) FROM outbox_tasks WHERE status='failed' GROUP BY 1",
    "users": "SELECT state,language,count(*) FROM users GROUP BY 1,2",
    "filters": "SELECT is_enabled,deleted_at IS NOT NULL AS deleted,count(*) FROM filters GROUP BY 1,2",
    "payments": "SELECT count(*) FROM payments",
    "channel_records": "SELECT status,count(*),count(sent_at) AS with_sent_at FROM channel_posts GROUP BY 1",
    "recent_channel_scope": """SELECT (c.sent_at AT TIME ZONE 'Asia/Baku')::date AS day,count(*) AS sent,
      count(*) FILTER(WHERE payload->>'city' IS DISTINCT FROM 'Bakı' OR payload->>'deal_type' IS DISTINCT FROM 'rent' OR COALESCE(payload->>'category_slug','') NOT IN ('menziller/yeni-tikili','menziller/kohne-tikili')) AS outside_scope
      FROM channel_posts c JOIN listings l ON l.id=c.listing_id WHERE c.sent_at >= '2026-08-16T20:00:00Z' GROUP BY 1 ORDER BY 1""",
    "db_size": "SELECT pg_database_size(current_database()) AS bytes",
    "daily": """WITH days AS (
      SELECT generate_series('2026-08-15'::date,'2026-09-12'::date,'1 day')::date AS day)
      SELECT day,
      (SELECT count(*) FROM listings WHERE (first_seen_at AT TIME ZONE 'Asia/Baku')::date=day) AS first_seen,
      (SELECT count(*) FROM channel_posts WHERE (created_at AT TIME ZONE 'Asia/Baku')::date=day) AS channel_queued,
      (SELECT count(*) FROM channel_posts WHERE (sent_at AT TIME ZONE 'Asia/Baku')::date=day) AS channel_sent,
      (SELECT count(*) FROM deliveries WHERE (sent_at AT TIME ZONE 'Asia/Baku')::date=day) AS private_sent
      FROM days ORDER BY day""",
    "channel_current_payload_check": """SELECT count(*) AS sent,
      count(*) FILTER(WHERE payload->>'city' IS DISTINCT FROM 'Bakı'
        OR payload->>'deal_type' IS DISTINCT FROM 'rent'
        OR COALESCE(payload->>'category_slug','') NOT IN ('menziller/yeni-tikili','menziller/kohne-tikili')) AS outside_scope,
      count(DISTINCT c.listing_id) AS unique_listings,
      count(*) FILTER(WHERE c.sent_at-c.created_at>interval '5 minutes') AS queue_over_5m,
      percentile_cont(0.95) WITHIN GROUP(ORDER BY extract(epoch FROM c.sent_at-c.created_at)) AS p95_queue_seconds
      FROM channel_posts c JOIN listings l ON l.id=c.listing_id WHERE c.sent_at IS NOT NULL""",
    "channel_periods": """SELECT payload->>'rent_period' AS period,count(*) FROM channel_posts c JOIN listings l ON l.id=c.listing_id WHERE c.sent_at IS NOT NULL GROUP BY 1""",
    "sample_last_sent": """SELECT l.source_listing_id,l.payload->>'listing_url' AS url,
      l.payload->>'updated_at' AS source_updated,l.first_seen_at,c.created_at AS queued,c.sent_at
      FROM channel_posts c JOIN listings l ON l.id=c.listing_id WHERE c.sent_at IS NOT NULL ORDER BY c.sent_at DESC LIMIT 5""",
    "private_current_filter_check": """SELECT d.id,d.telegram_user_id,l.payload FROM deliveries d JOIN listings l ON l.id=d.listing_id WHERE d.sent_at IS NOT NULL""",
}


def main():
    report = {}
    with psycopg.connect(os.environ['DATABASE_URL'], row_factory=dict_row) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        conn.execute("SET LOCAL statement_timeout='30s'")
        for name, query in QUERIES.items():
            rows = conn.execute(query).fetchall()
            if name == 'private_current_filter_check':
                from server.matching import matches
                rules = conn.execute('SELECT telegram_user_id,basic,additional FROM filters WHERE deleted_at IS NULL AND is_enabled').fetchall()
                report[name] = {'sent':len(rows), 'match_current_active_filter':sum(any(r['telegram_user_id']==d['telegram_user_id'] and matches(d['payload'],r['basic'],r['additional']) for r in rules) for d in rows), 'historical_rules_available':False}
            else:
                report[name] = rows
    report['code_sha256_lf'] = {name:hashlib.sha256(Path(name).read_text().encode()).hexdigest() for name in ['server/app.py','server/worker.py','server/bot_ui.py','server/matching.py']}
    report['safe_settings'] = {key:os.getenv(key) for key in ['ENABLE_PUBLIC_CHANNEL','MAX_PUBLIC_AGE_HOURS','MAX_PRIVATE_AGE_HOURS','WORKER_QUEUE']}
    print(json.dumps(report,ensure_ascii=False,default=str,indent=2))


if __name__ == '__main__':
    main()
