"""One-time, auditable import from a manually exported ID file; never reads GitHub Secrets."""
import os
from pathlib import Path

from .db import connect, migrate


def main() -> None:
    path = Path(os.environ["LEGACY_USER_IDS_FILE"])
    ids = sorted({int(line.strip()) for line in path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.lstrip().startswith("#")})
    migrate()
    with connect() as conn, conn.cursor() as cur:
        for user_id in ids:
            cur.execute("""INSERT INTO users(telegram_user_id,chat_id,state,language) VALUES(%s,%s,'approved','ru')
              ON CONFLICT(telegram_user_id) DO UPDATE SET state='approved',updated_at=now()""",(user_id,user_id))
            cur.execute("INSERT INTO user_access_audit(telegram_user_id,action,details) VALUES(%s,'legacy_import','{\"source\":\"manual_export\"}'::jsonb)",(user_id,))
    print(f"approved_imported={len(ids)}")


if __name__ == '__main__': main()
