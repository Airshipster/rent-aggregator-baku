"""Owner-only operational alerts; called by this bot's isolated host timer."""
import json
import os
from server.db import connect
from src.telegram_client import TelegramClient
from src.telegram_errors import redact_error


def main():
    alerts=[]
    with connect() as c:
        source=c.execute("SELECT last_error,details FROM service_health WHERE name='collector'").fetchone()
        if source and source['details'].get('phase')=='source_blocked':
            alerts.append(('source-denied','Сборщик на сервере получает HTTP 403 от Bina. Доставка за 5 минут пока не обеспечена. GitHub оставлен действующим сборщиком.'))
        row=c.execute("SELECT count(*) n FROM outbox_tasks WHERE status='uncertain'").fetchone()
        channel=c.execute("SELECT count(*) n FROM channel_outbox_tasks WHERE status='uncertain'").fetchone()
        if row['n']+channel['n']:
            alerts.append(('uncertain','Есть отправки с неизвестным результатом. Они не будут повторены автоматически, чтобы не создать дубликаты. Нужна сверка журнала.'))
        ingest=c.execute("SELECT max(received_at)<now()-interval '15 minutes' stale FROM ingest_requests").fetchone()
        if ingest and ingest['stale']:
            alerts.append(('ingest-stale','Новых данных от сборщиков не было более 15 минут. Это сбой целевой частоты обновления, даже если сервер отвечает на команды.'))
    if not alerts:
        return
    # One combined alert per six hours, with a committed claim before the network.
    with connect() as c:
        claimed=c.execute("""INSERT INTO service_health(name,details) VALUES('operations-alert',%s::jsonb)
          ON CONFLICT(name) DO UPDATE SET heartbeat_at=now(),details=EXCLUDED.details
          WHERE service_health.heartbeat_at<now()-interval '6 hours' RETURNING name""",(json.dumps({'reasons':[a[0] for a in alerts]}),)).fetchone()
    if not claimed:
        return
    uid=int(os.environ['TELEGRAM_ADMIN_USER_ID'])
    with connect() as c:
        admin=c.execute('SELECT chat_id FROM users WHERE telegram_user_id=%s',(uid,)).fetchone()
    try:
        result=TelegramClient(defer_retries=True).send_message(str(admin['chat_id']),'Техническое состояние бота\n\n'+'\n\n'.join(a[1] for a in alerts))
        with connect() as c:
            c.execute("INSERT INTO bot_messages(telegram_user_id,chat_id,telegram_message_id,kind) VALUES(%s,%s,%s,'operations-alert') ON CONFLICT DO NOTHING",(uid,admin['chat_id'],result['message_id']))
            c.execute("UPDATE service_health SET last_success_at=now(),last_error=NULL WHERE name='operations-alert'")
    except Exception as error:
        with connect() as c:
            c.execute("UPDATE service_health SET last_error=%s WHERE name='operations-alert'",(redact_error(error),))
        raise


if __name__=='__main__': main()
