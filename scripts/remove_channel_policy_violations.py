import argparse
import os
from datetime import timedelta

import psycopg
import requests
from psycopg.rows import dict_row

from src.utils import image_datetime, parse_dt


def violations(connection: psycopg.Connection, limit: int) -> list[dict]:
    with connection.cursor() as cursor:
        cursor.execute(
            """SELECT c.id,c.chat_id,c.telegram_message_id,c.created_at,l.payload
               FROM channel_posts c
               JOIN listings l ON l.id=c.listing_id
               WHERE c.status='sent' AND c.telegram_message_id IS NOT NULL
               ORDER BY c.sent_at DESC
               LIMIT %s""",
            (limit,),
        )
        result = []
        for row in cursor.fetchall():
            payload = row["payload"]
            source_date = image_datetime(payload.get("first_image_url")) or parse_dt(payload.get("updated_at"))
            if source_date and source_date < row["created_at"] - timedelta(hours=168):
                result.append(row)
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=37)
    parser.add_argument("--expect", type=int, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as connection:
        rows = violations(connection, args.limit)
        print(f"checked={args.limit} violations={len(rows)} execute={args.execute}")
        if len(rows) != args.expect:
            raise RuntimeError(f"expected {args.expect} violations, found {len(rows)}")
        if not args.execute:
            return
        deleted = 0
        for row in rows:
            response = requests.post(
                f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/deleteMessage",
                json={"chat_id": row["chat_id"], "message_id": row["telegram_message_id"]},
                timeout=30,
            )
            document = response.json()
            description = document.get("description", "")
            if not document.get("ok") and "message to delete not found" not in description.lower():
                raise RuntimeError(f"Telegram deletion failed: {description}")
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE channel_posts
                       SET status='retired',updated_at=now(),last_error='removed after channel age-policy audit'
                       WHERE id=%s""",
                    (row["id"],),
                )
            connection.commit()
            deleted += 1
        print(f"deleted={deleted}")


if __name__ == "__main__":
    main()
