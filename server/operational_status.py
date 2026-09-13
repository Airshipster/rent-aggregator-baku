"""Owner-only operational alerts; called by this bot's isolated host timer."""
import json
import os
from server.db import connect
from src.telegram_client import TelegramClient
from src.telegram_errors import redact_error
from server.system_status import snapshot, incidents, render


def main():
    with connect() as c:
        data = snapshot(c.cursor())
    codes = incidents(data)
    previous = data['beats'].get('operations-alert',{})
    if not codes and not previous.get('details',{}).get('reasons'):
        return
    # Report changes once, not the same unresolved incident every six hours.
    with connect() as c:
        claimed=c.execute("""INSERT INTO service_health(name,details) VALUES('operations-alert',%s::jsonb)
          ON CONFLICT(name) DO UPDATE SET heartbeat_at=now(),details=EXCLUDED.details
          WHERE (service_health.details IS DISTINCT FROM EXCLUDED.details AND service_health.heartbeat_at<now()-interval '1 minute')
             OR (service_health.last_error IS NOT NULL AND service_health.heartbeat_at<now()-interval '15 minutes')
          RETURNING name""",(json.dumps({'reasons':codes}),)).fetchone()
    if not claimed:
        return
    uid=int(os.environ['TELEGRAM_ADMIN_USER_ID'])
    with connect() as c:
        admin=c.execute('SELECT chat_id FROM users WHERE telegram_user_id=%s',(uid,)).fetchone()
    try:
        title = '⚠️ Требуется внимание. Передайте коды ошибок в Codex.' if codes else '✅ Ранее обнаруженные сбои больше не наблюдаются.'
        result=TelegramClient(defer_retries=True).send_message(str(admin['chat_id']),title+'\n\n'+render(data,'ru'))
        with connect() as c:
            c.execute("INSERT INTO bot_messages(telegram_user_id,chat_id,telegram_message_id,kind) VALUES(%s,%s,%s,'operations-alert') ON CONFLICT DO NOTHING",(uid,admin['chat_id'],result['message_id']))
            c.execute("UPDATE service_health SET last_success_at=now(),last_error=NULL WHERE name='operations-alert'")
    except Exception as error:
        with connect() as c:
            c.execute("UPDATE service_health SET last_error=%s WHERE name='operations-alert'",(redact_error(error),))
        raise


if __name__=='__main__': main()
