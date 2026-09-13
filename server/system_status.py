"""Read-only operational evidence shared by the admin screen and alerts."""
from datetime import datetime, timezone
from html import escape
import os

LABELS = {
 'ru': ('Состояние системы','Связь','Успешно','нет данных','Ожидаемо','мин.','Очереди','ожидают','отложены','Ошибки','Задержка от первого обнаружения до отправки, p95','Время создания объявления источником пока не подтверждено.'),
 'az': ('Sistemin vəziyyəti','Əlaqə','Uğurlu','məlumat yoxdur','Gözlənilən','dəq.','Növbələr','gözləyir','təxirə salınıb','Xətalar','İlk aşkarlamadan göndərişə qədər gecikmə, p95','Mənbədə elanın yaradılma vaxtı hələ təsdiqlənməyib.'),
 'en': ('System status','Heartbeat','Success','no data','Expected','min','Queues','pending','held','Errors','First detection to delivery latency, p95','Original listing creation time is not yet verified.'),
}


def snapshot(cur):
    cur.execute('SELECT name,heartbeat_at,last_success_at,last_error,details FROM service_health')
    beats = {r['name']: r for r in cur.fetchall()}
    queues = {}
    cutoff = os.getenv('DELIVERY_NOT_BEFORE') or '9999-01-01T00:00:00Z'
    for name, table in [('channel','channel_outbox_tasks'),('private','outbox_tasks')]:
        cur.execute(f"""SELECT count(*) FILTER(WHERE status IN ('pending','failed') AND
            (task_type='mark_removed' OR created_at >= %s::timestamptz)) pending,
            count(*) FILTER(WHERE status IN ('pending','failed') AND task_type='send' AND created_at < %s::timestamptz) held,
            count(*) FILTER(WHERE status='uncertain') uncertain,
            count(*) FILTER(WHERE status='dead_letter') dead_letter,
            extract(epoch FROM now()-min(created_at) FILTER(WHERE status IN ('pending','failed') AND task_type='send'
                AND created_at >= %s::timestamptz)) oldest_seconds FROM {table}""",(cutoff,cutoff,cutoff))
        queues[name] = cur.fetchone()
    cur.execute("""SELECT percentile_cont(0.95) WITHIN GROUP(ORDER BY extract(epoch FROM p.sent_at-l.first_seen_at)) seconds,
        count(*) samples FROM channel_posts p JOIN listings l ON l.id=p.listing_id
        WHERE p.sent_at > now()-interval '24 hours' AND p.sent_at>=l.first_seen_at""")
    latency = cur.fetchone()
    return {'beats':beats,'queues':queues,'latency':latency,'now':datetime.now(timezone.utc)}


def age(when, now):
    return max(0,(now-when).total_seconds()) if when else None


def incidents(data):
    result = []
    beats, now = data['beats'], data['now']
    source = beats.get('collector',{})
    if source.get('details',{}).get('phase') == 'source_blocked':
        result.append('BINA_ACCESS_DENIED')
    elif source.get('last_error'):
        result.append('COLLECTOR_FAILED')
    if beats.get('removal-check',{}).get('last_error'):
        result.append('STATUS_CHECK_FAILED')
    if age(source.get('last_success_at'),now) is None or age(source.get('last_success_at'),now)>300:
        result.append('COLLECTOR_STALE')
    for name in ('channel','private'):
        worker = beats.get('worker-'+name,{})
        if age(worker.get('heartbeat_at'),now) is None or age(worker.get('heartbeat_at'),now)>120:
            result.append('WORKER_'+name.upper()+'_STALE')
        queue = data['queues'][name]
        if queue['uncertain']:
            result.append('DELIVERY_'+name.upper()+'_UNCERTAIN')
        if queue['dead_letter']:
            result.append('DELIVERY_'+name.upper()+'_FAILED')
        if (queue['oldest_seconds'] or 0)>300:
            result.append('DELIVERY_'+name.upper()+'_LAG')
    return result


def render(data, language='ru'):
    title,link,success,unknown,expected,minute,queue_label,pending,held,errors,latency,note = LABELS.get(language,LABELS['ru'])
    lines = ['<b>📡 '+title+'</b>']
    for name,normal,threshold in [('collector',2,5),('removal-check',2,5),('worker-channel',0.5,2),('worker-private',0.5,2),('github-standby',5,30)]:
        beat = data['beats'].get(name,{})
        elapsed = age(beat.get('last_success_at'),data['now'])
        icon = '⚪' if elapsed is None else '❌' if beat.get('last_error') else '⚠️' if elapsed>threshold*60 else '✅'
        def fmt(value):
            n = age(value,data['now'])
            return unknown if n is None else f'{n/60:.1f} {minute}'
        lines += ['',f'{icon} <b>{name}</b>',f'{success}: {fmt(beat.get("last_success_at"))} · {link}: {fmt(beat.get("heartbeat_at"))}',f'{expected}: {normal} {minute}']
    lines += ['', '<b>'+queue_label+'</b>']
    for name,q in data['queues'].items():
        lines.append(f'{name}: {pending} {q["pending"]}, {held} {q["held"]}')
    lag = data['latency']
    lines += ['',f'{latency}: '+(f'{lag["seconds"]/60:.1f} {minute} (n={lag["samples"]})' if lag['samples'] else unknown),note]
    codes = incidents(data)
    if codes:
        lines += ['', '<b>'+errors+'</b>', '\n'.join('<code>'+escape(code)+'</code>' for code in codes)]
    return '\n'.join(lines)
