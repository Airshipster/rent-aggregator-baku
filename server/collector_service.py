"""Server collection with a durable discovery queue and payload spool."""
import json
import os
import time
from .db import connect, migrate
from .health import beat
from src.central_ingest import listing_payload
from src.collector import filters
from src.source_client import SourceClient, SourceBlockedError
from src.source_parser import SourceParser
from src.telegram_errors import redact_error
from src.utils import env_int, is_recent, sleep_soft


def store_spool():
    from .app import _store_ingest
    with connect() as c:
        rows = c.execute('SELECT id,payload FROM collector_spool WHERE accepted_at IS NULL ORDER BY created_at LIMIT 100').fetchall()
    for row in rows:
        body = json.dumps({'listings':[row['payload']]},ensure_ascii=False,separators=(',',':')).encode()
        _store_ingest(body, 'server:'+str(row['id']))
        with connect() as c:
            c.execute('UPDATE collector_spool SET accepted_at=now() WHERE id=%s',(row['id'],))
    return len(rows)


def check_published_statuses(parser):
    # Keep a durable round-robin cursor; only inspect listings we have delivered.
    limit = min(50, max(0, env_int('REMOVAL_CHECKS_PER_RUN', 50)))
    if not limit:
        return
    with connect() as c:
        cursor = c.execute("SELECT details FROM service_health WHERE name='removal-cursor'").fetchone()
        after = (cursor or {}).get('details', {}).get('after', '00000000-0000-0000-0000-000000000000')
        sql = """SELECT l.id,l.source,l.source_listing_id FROM listings l
            WHERE l.status='active' AND l.source IN ('source','bina.az') AND l.id > %s::uuid AND
              (EXISTS(SELECT 1 FROM channel_posts p WHERE p.listing_id=l.id AND p.telegram_message_id IS NOT NULL)
               OR EXISTS(SELECT 1 FROM deliveries d WHERE d.listing_id=l.id AND d.telegram_message_id IS NOT NULL))
            ORDER BY l.id LIMIT %s"""
        rows = c.execute(sql, (after, limit)).fetchall()
        if not rows:
            rows = c.execute(sql, ('00000000-0000-0000-0000-000000000000', limit)).fetchall()
    try:
        statuses = parser.check_statuses([row['source_listing_id'] for row in rows])
    except SourceBlockedError:
        raise
    except Exception as error:
        beat('removal-check',error=redact_error(error),phase='failed')
        return
    for row in rows:
        try:
            status = statuses[row['source_listing_id']]
            if status != 'active':
                payload = {'listing_id':row['source_listing_id'], 'source':row['source'],
                           'listing_url':parser.client.base_url+'/items/'+row['source_listing_id'],
                           'is_deleted':True, 'raw_status':status}
                with connect() as c:
                    c.execute('INSERT INTO collector_spool(source_listing_id,payload) VALUES(%s,%s::jsonb)',
                              (row['source_listing_id'],json.dumps(payload)))
                store_spool()
        except SourceBlockedError:
            raise
        except Exception as error:
            # Unknown is not deleted. Stop this pass so the failed item is retried.
            beat('removal-check',error=redact_error(error),phase='failed')
            return
        beat('removal-cursor',success=True,after=str(row['id']))
    beat('removal-check',success=True,checked=len(rows))


def cycle():
    started = time.monotonic()
    parser = SourceParser(SourceClient())
    beat('collector',phase='source_start')
    # Collection uses GraphQL; HTML availability is not an API prerequisite.
    queries = filters()
    cities = parser.list_cities()
    with connect() as c:
        row = c.execute("SELECT details FROM service_health WHERE name='collector-cursor'").fetchone()
    cursor = int((row or {}).get('details',{}).get('cursor',0)) % max(1,len(cities))
    if cities:
        queries += [{**q,'cityId':cities[cursor][0]} for q in filters()]
    discovered = 0
    for query in queries:
        beat('collector',phase='discover',discovered=discovered)
        summaries = parser.list_recent(env_int('MAX_LISTINGS_PER_RUN',100),pages=env_int('LIST_PAGES_PER_RUN',2),item_filter=query)
        with connect() as c:
            for summary in summaries:
                if not is_recent(summary.updated_at,168):
                    continue
                c.execute("""INSERT INTO collector_candidates(source_listing_id,source_updated_at)
                    VALUES(%s,%s) ON CONFLICT(source_listing_id) DO UPDATE SET
                    status=CASE WHEN collector_candidates.source_updated_at IS DISTINCT FROM EXCLUDED.source_updated_at THEN 'pending' ELSE collector_candidates.status END,
                    next_retry_at=CASE WHEN collector_candidates.source_updated_at IS DISTINCT FROM EXCLUDED.source_updated_at THEN now() ELSE collector_candidates.next_retry_at END,
                    source_updated_at=EXCLUDED.source_updated_at""",(summary.listing_id,summary.updated_at))
                discovered += 1
    beat('collector-cursor',success=True,cursor=(cursor+1)%max(1,len(cities)))
    check_published_statuses(parser)
    with connect() as c:
        c.execute("UPDATE collector_candidates SET status='expired' WHERE status='pending' AND source_updated_at < now()-interval '7 days'")
        candidates = c.execute("""SELECT source_listing_id FROM collector_candidates cc WHERE status='pending' AND next_retry_at<=now()
            ORDER BY EXISTS(SELECT 1 FROM listings l WHERE l.source IN ('source','bina.az') AND l.source_listing_id=cc.source_listing_id),
            source_updated_at DESC NULLS LAST LIMIT %s""",(env_int('MAX_DETAIL_FETCHES_PER_RUN',100),)).fetchall()
    fetched = 0
    for row in candidates:
        # Leave unprocessed rows durable for the next pass, keeping discovery frequent.
        if time.monotonic()-started >= max(30,env_int('COLLECTOR_CYCLE_BUDGET_SECONDS',90)):
            break
        source_id = row['source_listing_id']
        beat('collector',phase='detail',fetched=fetched)
        sleep_soft()
        try:
            detail = parser.get_detail(source_id)
            if detail is None:
                # A parser omission is not evidence that the listing was deleted.
                raise ValueError('empty detail response')
            payload = listing_payload(detail,'rent' if detail.rent_period in {'daily','monthly'} else 'sale')
            payload['channel_candidate'] = True
            with connect() as c:
                c.execute('INSERT INTO collector_spool(source_listing_id,payload) VALUES(%s,%s::jsonb)',(source_id,json.dumps(payload)))
                c.execute("UPDATE collector_candidates SET status='fetched',fetched_at=now(),last_error=NULL WHERE source_listing_id=%s",(source_id,))
            fetched += 1
        except SourceBlockedError:
            raise
        except Exception as error:
            with connect() as c:
                c.execute("UPDATE collector_candidates SET attempts=attempts+1,last_error=%s,next_retry_at=now()+interval '10 minutes' WHERE source_listing_id=%s",(redact_error(error),source_id))
        # Submit continuously, not only after the slowest listing in a batch.
        store_spool()
    return discovered, fetched


def main():
    migrate()
    interval = max(60,env_int('COLLECTOR_INTERVAL_SECONDS',120))
    while True:
        started = time.monotonic()
        wait = interval
        try:
            with connect() as lock:
                lock.autocommit = True
                acquired = lock.execute("SELECT pg_try_advisory_lock(hashtext('rent-collector-singleton')) locked").fetchone()['locked']
                if not acquired:
                    time.sleep(10)
                    continue
                store_spool()
                discovered,fetched = cycle()
                with connect() as c:
                    row = c.execute("SELECT heartbeat_at > now()-interval '4 hours' ready FROM service_health WHERE name='github-standby'").fetchone()
                beat('collector',success=True,phase='idle',discovered=discovered,fetched=fetched,
                     standby_recently_ready=bool(row and row['ready']),duration_seconds=round(time.monotonic()-started,2))
        except SourceBlockedError as error:
            # Do not change identities or switch IPs to evade an access restriction.
            wait = 900
            beat('collector',error=str(error),phase='source_blocked',retry_seconds=wait)
        except Exception as error:
            wait = 60
            try:
                beat('collector',error=redact_error(error),phase='failed')
            except Exception:
                pass
            print('collector_error='+redact_error(error),flush=True)
        time.sleep(max(1,wait-(time.monotonic()-started)))


if __name__ == '__main__':
    main()
