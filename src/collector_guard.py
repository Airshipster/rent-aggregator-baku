"""GitHub standby readiness probe; source denial is not a failover trigger."""
import hashlib
import hmac
import json
import os
import requests


def should_collect():
    if os.getenv('COLLECTOR_ROLE') != 'standby':
        return True
    body = b'{"component":"github-standby"}'
    signature = hmac.new(os.environ['CENTRAL_INGEST_SHARED_SECRET'].encode(),body,hashlib.sha256).hexdigest()
    url = os.environ['CENTRAL_INGEST_URL'].rstrip('/')+'/v1/collector/status'
    response = requests.post(url,data=body,headers={'X-Signature':signature,'Content-Type':'application/json'},timeout=20)
    response.raise_for_status()
    status = response.json()
    if status.get('source_blocked'):
        raise RuntimeError('Source access denied: fallback must not bypass the restriction')
    print('collector_role=standby primary_active='+str(status['primary_active']).lower())
    return not status['primary_active']


if __name__ == '__main__':
    from .collector import main
    if should_collect():
        main()
