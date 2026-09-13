import sys
from .db import connect


def healthy(name):
    with connect() as c:
        row = c.execute("""SELECT extract(epoch FROM now()-heartbeat_at) age,details
            FROM service_health WHERE name=%s""",(name,)).fetchone()
    if not row:
        return False
    limit = 180
    if name == 'collector' and row['details'].get('phase')=='source_blocked':
        limit = int(row['details'].get('retry_seconds',900))+120
    return row['age'] < limit


if __name__ == '__main__':
    raise SystemExit(0 if healthy(sys.argv[1]) else 1)
