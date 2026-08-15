import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import FastAPI, Header, HTTPException, Request

from .db import connect, migrate
from .i18n import t
from .matching import matches
from .bot_ui import handle_update
from src.utils import env_int, image_datetime, is_recent, parse_dt

app = FastAPI(title="Rent Aggregator Baku")


def _public_channel_enabled() -> bool:
    return os.getenv("ENABLE_PUBLIC_CHANNEL", "false").lower() in {"1", "true", "yes", "on"}


def _public_channel_eligible(payload: dict[str, Any]) -> bool:
    source_date = image_datetime(payload.get("first_image_url")) or parse_dt(payload.get("updated_at"))
    return (
        _public_channel_enabled()
        and payload.get("channel_candidate", True)
        and payload.get("deal_type") == "rent"
        and payload.get("city") == "Bakı"
        and payload.get("category_slug") in {"menziller/yeni-tikili", "menziller/kohne-tikili"}
        and is_recent(source_date, env_int("MAX_PUBLIC_AGE_HOURS", 168))
    )


def _verify_ingest(body: bytes, signature: str | None) -> None:
    expected = hmac.new(os.environ["INGEST_SHARED_SECRET"].encode(), body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "invalid ingest signature")


def _tg(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{method}", json=payload, timeout=20)
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API error"))
    return data["result"]


def _upsert_user(cur, user: dict[str, Any], chat_id: int) -> None:
    cur.execute("""INSERT INTO users (telegram_user_id,chat_id,first_name,username)
        VALUES (%s,%s,%s,%s) ON CONFLICT (telegram_user_id) DO UPDATE SET
        chat_id=EXCLUDED.chat_id,first_name=EXCLUDED.first_name,username=EXCLUDED.username,updated_at=now()""",
        (user["id"], chat_id, user.get("first_name"), user.get("username")))


def _buttons(language: str, approved: bool) -> dict[str, Any]:
    if not approved:
        return {"inline_keyboard":[[{"text":t(language,"apply"),"callback_data":"apply"}]]}
    labels = t(language, "menu").split("|")
    return {"inline_keyboard":[[{"text":labels[0],"callback_data":"filter:new"}], [{"text":labels[1],"callback_data":"filter:list"}], [{"text":labels[2],"callback_data":"additional"}], [{"text":labels[3],"callback_data":"settings"}]]}


def _send_access_screen(chat_id: int, language: str, approved: bool) -> None:
    _tg("sendMessage", {"chat_id":chat_id, "text":t(language,"approved" if approved else "closed"), "reply_markup":_buttons(language, approved)})


def _filter_question(chat_id: int, language: str, filter_id: str, step: str) -> None:
    if step == "deal":
        text, choices = ("Тип сделки", [("Аренда","rent"),("Покупка","sale"),("Посуточно","daily")])
    elif step == "category":
        text, choices = ("Тип объекта", [("Новостройка","yeni-tikili"),("Вторичка","kohne-tikili"),("Дом/вилла","house"),("Офис","office"),("Земля","land"),("Коммерция","commercial")])
    else:
        text, choices = ("Количество комнат", [("Любое","any"),("1","1"),("2","2"),("3","3"),("4+","4")])
    _tg("sendMessage", {"chat_id":chat_id,"text":text,"reply_markup":{"inline_keyboard":[[{"text":label,"callback_data":f"f:{filter_id}:{step}:{value}"}] for label,value in choices]}})


@app.on_event("startup")
def startup() -> None:
    migrate()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    with connect() as conn:
        conn.execute("SELECT 1")
    return {"status":"ok"}


@app.post("/telegram-bots/rent-aggregator-baku/v1/ingest/listings")
async def ingest(request: Request, x_signature: str | None = Header(None), x_idempotency_key: str | None = Header(None)) -> dict[str, int]:
    body = await request.body()
    _verify_ingest(body, x_signature)
    if not x_idempotency_key:
        raise HTTPException(400, "missing idempotency key")
    document = json.loads(body)
    listings = document.get("listings") or []
    digest = hashlib.sha256(body).hexdigest()
    inserted = queued = 0
    with connect() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO ingest_requests(idempotency_key,body_sha256) VALUES(%s,%s) ON CONFLICT DO NOTHING RETURNING idempotency_key", (x_idempotency_key,digest))
        if not cur.fetchone():
            return {"received":len(listings),"inserted":0,"queued":0,"duplicate":1}
        for payload in listings:
            source, source_id = payload.get("source", "bina.az"), str(payload["listing_id"])
            status = "removed" if payload.get("is_deleted") else "active"
            cur.execute("""INSERT INTO listings(source,source_listing_id,payload,status,removed_at)
              VALUES(%s,%s,%s::jsonb,%s,CASE WHEN %s='removed' THEN now() END)
              ON CONFLICT(source,source_listing_id) DO UPDATE SET
              payload=CASE WHEN EXCLUDED.status='removed' THEN listings.payload || jsonb_build_object('is_deleted',true,'raw_status','removed') ELSE EXCLUDED.payload END,
              last_seen_at=now(),
              status=EXCLUDED.status,removed_at=CASE WHEN EXCLUDED.status='removed' THEN now() ELSE NULL END
              RETURNING id,(xmax=0) AS new_row,status""", (source,source_id,json.dumps(payload),status,status))
            row = cur.fetchone(); listing_id = row["id"]; inserted += int(row["new_row"])
            if status == "removed":
                cur.execute("""INSERT INTO outbox_tasks(delivery_id,task_type)
                    SELECT id,'mark_removed' FROM deliveries WHERE listing_id=%s AND telegram_message_id IS NOT NULL
                    ON CONFLICT(delivery_id,task_type) DO NOTHING""", (listing_id,))
                cur.execute("""INSERT INTO channel_outbox_tasks(channel_post_id,task_type)
                    SELECT id,'mark_removed' FROM channel_posts WHERE listing_id=%s AND telegram_message_id IS NOT NULL AND status='sent'
                    ON CONFLICT(channel_post_id,task_type) DO NOTHING""", (listing_id,))
                continue
            if not row["new_row"]:
                continue
            if _public_channel_eligible(payload):
                cur.execute("""INSERT INTO channel_posts(listing_id,chat_id) VALUES(%s,%s)
                    ON CONFLICT(listing_id) DO NOTHING RETURNING id""", (listing_id, int(os.environ["TELEGRAM_PUBLIC_CHANNEL_ID"])))
                channel_post = cur.fetchone()
                if channel_post:
                    cur.execute("INSERT INTO channel_outbox_tasks(channel_post_id,task_type) VALUES(%s,'send') ON CONFLICT DO NOTHING", (channel_post["id"],))
            cur.execute("""SELECT f.telegram_user_id,u.chat_id,f.basic,f.additional FROM filters f
              JOIN users u USING(telegram_user_id) WHERE f.is_enabled AND f.deleted_at IS NULL AND u.state='approved'""")
            for candidate in cur.fetchall():
                if not matches(payload, candidate["basic"], candidate["additional"]):
                    continue
                cur.execute("""INSERT INTO deliveries(listing_id,telegram_user_id,chat_id) VALUES(%s,%s,%s)
                  ON CONFLICT(listing_id,telegram_user_id) DO NOTHING RETURNING id""", (listing_id,candidate["telegram_user_id"],candidate["chat_id"]))
                delivery = cur.fetchone()
                if delivery:
                    cur.execute("INSERT INTO outbox_tasks(delivery_id,task_type) VALUES(%s,'send') ON CONFLICT DO NOTHING", (delivery["id"],)); queued += 1
    return {"received":len(listings),"inserted":inserted,"queued":queued,"duplicate":0}


@app.post("/telegram-bots/rent-aggregator-baku/webhook")
async def telegram_webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(None)) -> dict[str, bool]:
    if not hmac.compare_digest(x_telegram_bot_api_secret_token or "", os.environ["TELEGRAM_WEBHOOK_SECRET"]):
        raise HTTPException(401, "invalid webhook secret")
    update = await request.json()
    return handle_update(update)
    # Legacy handler retained below temporarily for rollback reference.
    with connect() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO telegram_updates(update_id) VALUES(%s) ON CONFLICT DO NOTHING RETURNING update_id", (update.get("update_id"),))
        if not cur.fetchone(): return {"ok":True}
        message = update.get("message") or update.get("callback_query",{}).get("message") or {}
        user = update.get("message",{}).get("from") or update.get("callback_query",{}).get("from") or {}
        if not message or not user: return {"ok":True}
        chat_id, uid = int(message["chat"]["id"]), int(user["id"])
        _upsert_user(cur,user,chat_id)
        cur.execute("SELECT state,language,language_selected FROM users WHERE telegram_user_id=%s",(uid,)); profile=cur.fetchone(); language=profile["language"]
        data=(update.get("callback_query") or {}).get("data",""); text=(update.get("message") or {}).get("text","")
        callback_id=(update.get("callback_query") or {}).get("id")
        admin_id=int(os.environ["TELEGRAM_ADMIN_USER_ID"])
        if callback_id:
            _tg("answerCallbackQuery", {"callback_query_id": callback_id})
        if data.startswith("admin:") and uid==admin_id:
            action,target=data.split(":")[1:]; new_state="approved" if action=="approve" else "rejected"
            cur.execute("UPDATE users SET state=%s,updated_at=now() WHERE telegram_user_id=%s",(new_state,int(target)))
            cur.execute("INSERT INTO user_access_audit(telegram_user_id,action,actor_telegram_user_id) VALUES(%s,%s,%s)",(int(target),new_state,uid))
            if new_state=="approved":
                cur.execute("SELECT chat_id,language FROM users WHERE telegram_user_id=%s",(int(target),)); target_user=cur.fetchone(); _send_access_screen(target_user["chat_id"],target_user["language"],True)
            return {"ok":True}
        if data.startswith("lang:"):
            language=data.split(":",1)[1]; cur.execute("UPDATE users SET language=%s,language_selected=true WHERE telegram_user_id=%s",(language,uid)); _send_access_screen(chat_id,language,profile["state"]=="approved"); return {"ok":True}
        if data=="apply" and profile["state"]!="approved":
            cur.execute("INSERT INTO user_access_audit(telegram_user_id,action) VALUES(%s,'application')",(uid,))
            _tg("sendMessage", {"chat_id":admin_id,"text":f"Заявка на доступ\nИмя: {user.get('first_name','')}\n@{user.get('username','')}\nTelegram ID: {uid}","reply_markup":{"inline_keyboard":[[{"text":"Одобрить","callback_data":f"admin:approve:{uid}"},{"text":"Отклонить","callback_data":f"admin:reject:{uid}"}]]}})
            _tg("sendMessage",{"chat_id":chat_id,"text":t(language,"sent")}); return {"ok":True}
        if profile["state"]!="approved":
            if text.startswith("/start"): _tg("sendMessage",{"chat_id":chat_id,"text":t(language,"language"),"reply_markup":{"inline_keyboard":[[{"text":"Русский","callback_data":"lang:ru"},{"text":"Azərbaycanca","callback_data":"lang:az"},{"text":"English","callback_data":"lang:en"}]]}})
            else: _send_access_screen(chat_id,language,False)
            return {"ok":True}
        if not profile["language_selected"]:
            _tg("sendMessage",{"chat_id":chat_id,"text":t(language,"language"),"reply_markup":{"inline_keyboard":[[{"text":"Русский","callback_data":"lang:ru"},{"text":"Azərbaycanca","callback_data":"lang:az"},{"text":"English","callback_data":"lang:en"}]]}})
            return {"ok":True}
        if data=="additional": _tg("sendMessage",{"chat_id":chat_id,"text":t(language,"warning")})
        elif data=="filter:new":
            cur.execute("INSERT INTO filters(telegram_user_id) VALUES(%s) RETURNING id",(uid,)); _filter_question(chat_id,language,str(cur.fetchone()["id"]),"deal")
        elif data=="filter:list":
            cur.execute("SELECT name,basic FROM filters WHERE telegram_user_id=%s AND deleted_at IS NULL ORDER BY created_at",(uid,)); rows=cur.fetchall()
            text="\n".join(f"{row['name']}: {json.dumps(row['basic'],ensure_ascii=False)}" for row in rows) or "Фильтров пока нет."
            _tg("sendMessage",{"chat_id":chat_id,"text":text})
        elif data.startswith("f:"):
            _,filter_id,step,value=data.split(":",3)
            cur.execute("SELECT basic FROM filters WHERE id=%s AND telegram_user_id=%s AND deleted_at IS NULL",(filter_id,uid)); row=cur.fetchone()
            if not row: return {"ok":True}
            basic=dict(row["basic"])
            if step=="deal": basic["deal_type"]=[value]; next_step="category"
            elif step=="category": basic["category_slug"]=[value]; next_step="rooms"
            else:
                if value!="any": basic["rooms_min"]=int(value)
                next_step="done"
            cur.execute("UPDATE filters SET basic=%s::jsonb,updated_at=now() WHERE id=%s",(json.dumps(basic),filter_id))
            if next_step=="done": _tg("sendMessage",{"chat_id":chat_id,"text":"Фильтр сохранён. В «Дополнительных условиях» можно сузить выбор; там неизвестные значения по умолчанию не исключаются."})
            else: _filter_question(chat_id,language,filter_id,next_step)
        elif data=="settings":
            rows=[[{"text":"Язык","callback_data":"settings:language"}],[{"text":"Оплата","callback_data":"settings:payment"}]]
            if uid==admin_id: rows.append([{"text":"Заявки на доступ","callback_data":"settings:applications"}])
            _tg("sendMessage",{"chat_id":chat_id,"text":"Настройки","reply_markup":{"inline_keyboard":rows}})
        elif data=="settings:language": _tg("sendMessage",{"chat_id":chat_id,"text":t(language,"language"),"reply_markup":{"inline_keyboard":[[{"text":"Русский","callback_data":"lang:ru"},{"text":"Azərbaycanca","callback_data":"lang:az"},{"text":"English","callback_data":"lang:en"}]]}})
        elif data=="settings:payment": _tg("sendMessage",{"chat_id":chat_id,"text":"Оплата пока недоступна. Доступ выдаётся администратором вручную."})
        elif data=="settings:applications" and uid==admin_id:
            cur.execute("SELECT telegram_user_id,first_name,username FROM users WHERE state='pending' ORDER BY created_at")
            pending=cur.fetchall(); text="\n".join(f"{x['telegram_user_id']} @{x['username'] or ''} {x['first_name'] or ''}" for x in pending) or "Новых заявок нет."
            _tg("sendMessage",{"chat_id":chat_id,"text":text})
        elif text.startswith("/start"): _send_access_screen(chat_id,language,True)
    return {"ok":True}
