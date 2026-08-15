import json
import os
import re
import time
from datetime import datetime, timedelta, timezone

import requests

from .db import connect, migrate
from src.formatter_private_rich import format_private_rich
from src.formatter_public_az import format_deleted_update, format_public
from src.models import ListingDetail
from src.telegram_client import TelegramClient
from src.utils import parse_dt


_last_channel_send = 0.0
_last_private_send: dict[int, float] = {}


def retry_at(attempt: int, error: Exception | str | None = None) -> datetime:
    match=re.search(r"retry after (\d+)",str(error or ""),re.I)
    seconds=int(match.group(1))+1 if match else min(3600,15*(2**min(attempt,8)))
    return datetime.now(timezone.utc)+timedelta(seconds=seconds)


def throttle_channel() -> None:
    global _last_channel_send
    interval=float(os.getenv("CHANNEL_SEND_INTERVAL_SECONDS","3.2"))
    wait=interval-(time.monotonic()-_last_channel_send)
    if wait>0:
        time.sleep(wait)
    _last_channel_send=time.monotonic()


def throttle_private(chat_id: int) -> None:
    interval=float(os.getenv("PRIVATE_SEND_INTERVAL_SECONDS","1.1"))
    last=_last_private_send.get(chat_id,0.0)
    wait=interval-(time.monotonic()-last)
    if wait>0:
        time.sleep(wait)
    _last_private_send[chat_id]=time.monotonic()


def telegram(method: str, payload: dict):
    response=requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}",json=payload,timeout=30)
    data=response.json()
    if not data.get("ok"): raise RuntimeError(data.get("description","Telegram API error"))
    return data["result"]


def listing(payload: dict) -> ListingDetail:
    values = {key: payload.get(key) for key in ListingDetail.__dataclass_fields__}
    values["updated_at"] = parse_dt(values.get("updated_at")) if isinstance(values.get("updated_at"), str) else values.get("updated_at")
    return ListingDetail(**values)


def process_channel_one() -> bool:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT o.id,o.task_type,o.attempts,c.id channel_post_id,c.chat_id,c.telegram_message_id,l.payload
          FROM channel_outbox_tasks o JOIN channel_posts c ON c.id=o.channel_post_id JOIN listings l ON l.id=c.listing_id
          WHERE (o.status IN ('pending','failed') AND o.next_retry_at<=now()) OR (o.status='processing' AND o.locked_at < now()-interval '5 minutes')
          ORDER BY o.created_at FOR UPDATE SKIP LOCKED LIMIT 1""")
        task=cur.fetchone()
        if not task: return False
        cur.execute("UPDATE channel_outbox_tasks SET status='processing',locked_at=now() WHERE id=%s",(task["id"],))
        try:
            item=listing(task["payload"])
            throttle_channel()
            if task["task_type"]=="send":
                msg=telegram("sendMessage",{"chat_id":task["chat_id"],"text":format_public(item),"parse_mode":"HTML","link_preview_options":{"url":item.listing_url,"prefer_large_media":True}})
                cur.execute("UPDATE channel_posts SET status='sent',telegram_message_id=%s,sent_at=now(),updated_at=now() WHERE id=%s",(msg["message_id"],task["channel_post_id"]))
            else:
                text="❌ <b>Elan silinib</b>\n\n"+format_public(item)
                telegram("editMessageText",{"chat_id":task["chat_id"],"message_id":task["telegram_message_id"],"text":text,"parse_mode":"HTML","link_preview_options":{"url":item.listing_url,"prefer_large_media":True}})
                cur.execute("UPDATE channel_posts SET status='removed',updated_at=now() WHERE id=%s",(task["channel_post_id"],))
            cur.execute("UPDATE channel_outbox_tasks SET status='sent',sent_at=now(),last_error=NULL WHERE id=%s",(task["id"],))
        except Exception as exc:
            attempts=task["attempts"]+1
            error=f"{type(exc).__name__}: {exc}"[:500]
            print(f"channel_delivery_error task={task['id']} attempt={attempts} error={error}", flush=True)
            due=retry_at(attempts,exc)
            cur.execute("UPDATE channel_outbox_tasks SET status='failed',attempts=%s,next_retry_at=%s,last_error=%s WHERE id=%s",(attempts,due,error,task["id"]))
            cur.execute("UPDATE channel_posts SET status='failed',attempts=attempts+1,next_retry_at=%s,last_error=%s,updated_at=now() WHERE id=%s",(due,error,task["channel_post_id"]))
        return True


def process_one() -> bool:
    with connect() as conn, conn.cursor() as cur:
        cur.execute("""SELECT o.id,o.task_type,o.attempts,d.id delivery_id,d.chat_id,d.telegram_message_id,l.payload,u.language
            FROM outbox_tasks o
            JOIN deliveries d ON d.id=o.delivery_id
            JOIN listings l ON l.id=d.listing_id
            JOIN users u ON u.telegram_user_id=d.telegram_user_id AND u.state='approved'
            WHERE (o.status IN ('pending','failed') AND o.next_retry_at<=now())
               OR (o.status='processing' AND o.locked_at < now() - interval '5 minutes')
            ORDER BY o.created_at
            FOR UPDATE SKIP LOCKED LIMIT 1""")
        task=cur.fetchone()
        if not task: return False
        cur.execute("UPDATE outbox_tasks SET status='processing',locked_at=now() WHERE id=%s",(task["id"],))
        try:
            throttle_private(int(task["chat_id"]))
            if task["task_type"]=="send":
                item=listing(task["payload"])
                rich_html,rich_media=format_private_rich(item,item.image_urls,task["language"])
                button={"ru":"Подробнее","az":"Ətraflı bax","en":"View details"}.get(task["language"],"Подробнее")
                msg=TelegramClient().send_rich_message(str(task["chat_id"]),rich_html,rich_media,button,item.listing_url,protect_content=True)
                cur.execute("UPDATE deliveries SET status='sent',telegram_message_id=%s,sent_at=now(),updated_at=now() WHERE id=%s",(msg["message_id"],task["delivery_id"]))
            else:
                try:
                    telegram("editMessageText",{"chat_id":task["chat_id"],"message_id":task["telegram_message_id"],"text":"❌ <b>Объявление удалено</b>","parse_mode":"HTML"})
                except Exception:
                    telegram("sendMessage",{"chat_id":task["chat_id"],"text":"❌ Объявление удалено","reply_to_message_id":task["telegram_message_id"]})
            cur.execute("UPDATE outbox_tasks SET status='sent',sent_at=now(),last_error=NULL WHERE id=%s",(task["id"],))
        except Exception as exc:
            attempts=task["attempts"]+1
            error=f"{type(exc).__name__}: {exc}"[:500]
            print(f"private_delivery_error task={task['id']} attempt={attempts} error={error}", flush=True)
            due=retry_at(attempts,exc)
            cur.execute("UPDATE outbox_tasks SET status='failed',attempts=%s,next_retry_at=%s,last_error=%s WHERE id=%s",(attempts,due,error,task["id"]))
            cur.execute("UPDATE deliveries SET status='failed',attempts=attempts+1,next_retry_at=%s,last_error=%s,updated_at=now() WHERE id=%s",(due,error,task["delivery_id"]))
        return True


def main() -> None:
    migrate()
    queue = os.getenv("WORKER_QUEUE", "both").lower()
    if queue not in {"channel", "private", "both"}:
        raise ValueError("WORKER_QUEUE must be channel, private, or both")
    while True:
        processed = False
        if queue in {"channel", "both"}:
            processed = process_channel_one()
        if queue in {"private", "both"} and (queue == "private" or not processed):
            processed = process_one()
        if not processed:
            time.sleep(2)


if __name__ == '__main__': main()
