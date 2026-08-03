import os
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
            for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
                cur.execute(path.read_text(encoding="utf-8"))
