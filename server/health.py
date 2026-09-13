import json
from .db import connect
from src.telegram_errors import redact_error


def beat(name, success=False, error=None, **details):
    with connect() as conn:
        conn.execute("""INSERT INTO service_health(name,last_success_at,last_error,details)
          VALUES(%s,CASE WHEN %s THEN now() END,%s,%s::jsonb)
          ON CONFLICT(name) DO UPDATE SET heartbeat_at=now(),
          last_success_at=CASE WHEN %s THEN now() ELSE service_health.last_success_at END,
          last_error=EXCLUDED.last_error,details=EXCLUDED.details""",
          (name,success,redact_error(error) if error else None,json.dumps(details),success))
