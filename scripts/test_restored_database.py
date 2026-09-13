"""SQL and delivery-failure drill. Refuses all non-test database names."""
import json
import os
import uuid
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
import requests
from server.db import connect,baseline_legacy,migrate
from server.retention import expire_pending
from server.delivery_queue import claim,finish
from server import worker
from src.telegram_errors import TelegramAPIError


def main():
    with connect() as c:
        if not c.info.dbname.startswith('rent_restore_'):
            raise RuntimeError('Refusing to test a non-restore database')
        counts = {t:c.execute(f'SELECT count(*) n FROM {t}').fetchone()['n']
                  for t in ['users','payments','listings','deliveries','outbox_tasks','channel_posts','channel_outbox_tasks']}
    baseline_legacy()
    migrate()
    migrate()
    expired=expire_pending()
    assert not any(expire_pending().values()), 'retention is not idempotent'
    with connect() as c:
        for t,n in counts.items():
            assert c.execute(f'SELECT count(*) n FROM {t}').fetchone()['n']==n, 'journal rows lost'
        for table in ['outbox_tasks','channel_outbox_tasks']:
            c.execute(f"UPDATE {table} SET status='cancelled' WHERE status IN ('pending','failed','processing')")
        c.execute("INSERT INTO users(telegram_user_id,chat_id,state) VALUES(-900000001,-900000001,'approved') ON CONFLICT DO NOTHING")
        c.execute("INSERT INTO filters(telegram_user_id,basic) VALUES(-900000001,'{}')")
    os.environ.update(TELEGRAM_ADMIN_USER_ID='-900000001',PRIVATE_DELIVERY_MODE='admin_only',
                      DELIVERY_ENABLED='true',DELIVERY_NOT_BEFORE=datetime.now(timezone.utc).isoformat(),ENABLE_PUBLIC_CHANNEL='true')
    def seed(queue,days=0):
        now=datetime.now(timezone.utc)
        payload={'listing_id':str(uuid.uuid4()),'city':'Bakı','deal_type':'rent','rent_period':'monthly',
                 'category_slug':'menziller/yeni-tikili','updated_at':now.isoformat(),'image_urls':[]}
        with connect() as c:
            lid=c.execute("INSERT INTO listings(source,source_listing_id,payload,first_seen_at) VALUES('integration',%s,%s::jsonb,%s) RETURNING id",
                (payload['listing_id'],json.dumps(payload),now-timedelta(days=days))).fetchone()['id']
            if queue=='channel':
                pid=c.execute('INSERT INTO channel_posts(listing_id,chat_id) VALUES(%s,-900000002) RETURNING id',(lid,)).fetchone()['id']
                tid=c.execute("INSERT INTO channel_outbox_tasks(channel_post_id,task_type) VALUES(%s,'send') RETURNING id",(pid,)).fetchone()['id']
            else:
                pid=c.execute('INSERT INTO deliveries(listing_id,telegram_user_id,chat_id) VALUES(%s,-900000001,-900000001) RETURNING id',(lid,)).fetchone()['id']
                tid=c.execute("INSERT INTO outbox_tasks(delivery_id,task_type) VALUES(%s,'send') RETURNING id",(pid,)).fetchone()['id']
        return tid
    cutoff=datetime.now(timezone.utc)-timedelta(minutes=1)
    for queue in ['channel','private']:
        seed(queue)
        task=claim(queue,cutoff)
        assert task and task.get('attempt_id')
        assert claim(queue,cutoff) is None, 'double claim'
        finish(queue,task,'sent',message_id=1)
        assert claim(queue,cutoff) is None, 'sent task retried'
        seed(queue,8)
        assert claim(queue,cutoff)=={'cancelled':True}, 'expired task accepted'
        seed(queue)
        with patch.object(worker,'send',side_effect=requests.Timeout('lost reply')):
            assert worker.process(queue)
        assert claim(queue,cutoff) is None, 'ambiguous send retried'
        seed(queue)
        with patch.object(worker,'send',side_effect=TelegramAPIError({'error_code':429,'parameters':{'retry_after':60}})):
            assert worker.process(queue)
        assert claim(queue,cutoff) is None, 'cooldown ignored'
        with connect() as c:
            c.execute('DELETE FROM telegram_cooldowns')
    # A worker disappearing after claim is quarantined on the next claim pass.
    seed('private')
    task=claim('private',cutoff)
    with connect() as c:
        c.execute("UPDATE outbox_tasks SET locked_at=now()-interval '10 minutes' WHERE id=%s",(task['id'],))
    assert claim('private',cutoff) is None
    with connect() as c:
        assert c.execute('SELECT status FROM outbox_tasks WHERE id=%s',(task['id'],)).fetchone()['status']=='uncertain'
    print(json.dumps({'restore_tested':True,'counts':counts,'expired_in_test':expired,'sql_delivery_drills_passed':True}))


if __name__=='__main__': main()
