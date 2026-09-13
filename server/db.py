import os
import hashlib
from pathlib import Path
import psycopg
from psycopg.rows import dict_row


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


def migrate() -> None:
    with connect() as conn:
        with conn.cursor() as cur:
            # App and worker start together; serialize their idempotent migrations.
            cur.execute("SELECT pg_advisory_xact_lock(hashtext('rent_aggregator_migrations'))")
            cur.execute('CREATE TABLE IF NOT EXISTS schema_migrations (name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())')
            cur.execute("SELECT to_regclass('public.listings') AS legacy, EXISTS(SELECT 1 FROM schema_migrations) AS versioned")
            state = cur.fetchone()
            if state['legacy'] and not state['versioned']:
                raise RuntimeError('Unversioned database: verify snapshot and explicitly baseline migrations 001-011 first')
            for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
                digest = hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                cur.execute('SELECT sha256 FROM schema_migrations WHERE name=%s', (path.name,))
                existing = cur.fetchone()
                if existing:
                    if existing['sha256'] != digest:
                        raise RuntimeError('Applied migration checksum changed: ' + path.name)
                    continue
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute('INSERT INTO schema_migrations(name,sha256) VALUES(%s,%s)', (path.name,digest))


def baseline_legacy():
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('rent_aggregator_migrations'))")
        # These queries validate the late legacy schema without modifying its rows.
        conn.execute('SELECT language_selected,wizard FROM users LIMIT 0')
        conn.execute('SELECT basic,additional,is_enabled,deleted_at FROM filters LIMIT 0')
        conn.execute('SELECT status,telegram_message_id FROM channel_posts LIMIT 0')
        conn.execute('SELECT * FROM access_identifiers LIMIT 0')
        conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations(name text PRIMARY KEY,sha256 text NOT NULL,applied_at timestamptz NOT NULL DEFAULT now())')
        for path in sorted(Path(__file__).with_name('migrations').glob('*.sql')):
            if int(path.name.split('_',1)[0]) > 11:
                continue
            digest = hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
            conn.execute('INSERT INTO schema_migrations(name,sha256) VALUES(%s,%s) ON CONFLICT DO NOTHING',(path.name,digest))


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--baseline-legacy']:
        baseline_legacy()
    else:
        migrate()
