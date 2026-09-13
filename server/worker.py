import os
import re
import time
from datetime import datetime, timedelta, timezone
import requests

from .db import migrate
from .delivery_queue import claim, finish, pause_bot
from .health import beat
from .retention import expire_pending
from src.formatter_private_rich import format_private_rich
from src.formatter_public_az import format_public
from src.models import ListingDetail
from src.telegram_client import TelegramClient
from src.telegram_errors import TelegramAPIError, redact_error
from src.utils import parse_dt


class DeliveryRejectedError(RuntimeError):
    pass


def retry_at(attempt, error=None):
    match = re.search(r'retry after (\d+)', str(error or ''), re.I)
    delay = getattr(error, 'retry_after', None)
    seconds = int(delay)+1 if delay is not None else int(match.group(1))+1 if match else min(3600,15*2**min(attempt,8))
    return datetime.now(timezone.utc)+timedelta(seconds=seconds)


def failure_status(attempts, error):
    if isinstance(error, DeliveryRejectedError):
        return 'dead_letter'
    if isinstance(error, TelegramAPIError):
        if error.code == 429:
            return 'failed'
        if error.code in {400,401,403,404}:
            return 'dead_letter'
    return 'dead_letter' if attempts >= 8 else 'failed'


def delivery_cutoff():
    if os.getenv('DELIVERY_ENABLED','false').lower() not in {'true','1','yes'}:
        return None
    cutoff = parse_dt(os.getenv('DELIVERY_NOT_BEFORE'))
    if cutoff is None or cutoff.tzinfo is None:
        raise ValueError('DELIVERY_NOT_BEFORE must be an approved timezone-aware cutoff')
    return cutoff


def listing(payload):
    values = {key:payload.get(key) for key in ListingDetail.__dataclass_fields__}
    if isinstance(values['updated_at'],str):
        values['updated_at'] = parse_dt(values['updated_at'])
    return ListingDetail(**values)


def send(queue, task):
    client = TelegramClient(defer_retries=True)
    item = listing(task['payload'])
    if task['task_type'] == 'mark_removed':
        text = {'ru':'❌ Объявление удалено','az':'❌ Elan silinib','en':'❌ Listing removed'}.get(task.get('language','az'))
        if queue == 'channel':
            return client.call('editMessageText',{'chat_id':task['chat_id'],'message_id':task['telegram_message_id'],
                'text':text+'\n\n'+format_public(item),'parse_mode':'HTML'})
        # Rich messages lack a verified lossless edit path; use one tracked reply.
        return client.call('sendMessage',{'chat_id':task['chat_id'],'text':text,
            'reply_parameters':{'message_id':task['telegram_message_id'],'allow_sending_without_reply':True}})
    if queue == 'channel':
        return client.call('sendMessage',{'chat_id':task['chat_id'],'text':format_public(item),'parse_mode':'HTML',
            'link_preview_options':{'url':item.listing_url,'prefer_large_media':True}})
    html, media = format_private_rich(item,item.image_urls,task['language'])
    button = {'ru':'Подробнее','az':'Ətraflı bax','en':'View details'}[task['language']]
    return client.send_rich_message(str(task['chat_id']),html,media,button,item.listing_url,protect_content=True)


def process(queue):
    cutoff = delivery_cutoff()
    if cutoff is None:
        return False
    task = claim(queue,cutoff)
    if task is None:
        return False
    if task.get('cancelled'):
        return True
    try:
        result = send(queue,task)
    except Exception as error:
        status = failure_status(task['attempts'],error)
        due = retry_at(task['attempts'],error)
        if isinstance(error,TelegramAPIError) and error.code==429:
            pause_bot(due)
        creates_message = task['task_type']=='send' or queue=='private'
        if creates_message and (isinstance(error,requests.RequestException) or not isinstance(error,TelegramAPIError) or (error.code or 500)>=500):
            status = 'uncertain'
        finish(queue,task,status,error=redact_error(error),due=due)
    else:
        # Commit failures here deliberately leave the claim processing/uncertain.
        finish(queue,task,'sent',message_id=result.get('message_id'))
    return True


def process_channel_one():
    return process('channel')


def process_one():
    return process('private')


def main():
    migrate()
    queue = os.getenv('WORKER_QUEUE','both')
    if queue not in {'channel','private','both'}:
        raise ValueError('Invalid WORKER_QUEUE')
    last_maintenance = 0
    while True:
        try:
            if time.monotonic()-last_maintenance >= 30:
                counts = expire_pending()
                beat('worker-'+queue,success=True,expired=counts,enabled=delivery_cutoff() is not None)
                last_maintenance = time.monotonic()
            for name in (['channel','private'] if queue=='both' else [queue]):
                processed = process(name)
                time.sleep(3.2 if name=='channel' and processed else 1.1 if processed else 1)
        except Exception as error:
            print('worker_error='+redact_error(error),flush=True)
            time.sleep(5)


if __name__ == '__main__':
    main()
