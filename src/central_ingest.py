import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import asdict

import requests

from .models import ListingDetail


def listing_payload(item: ListingDetail, deal_type: str | None = None) -> dict:
    payload = asdict(item)
    payload["updated_at"] = item.updated_at.isoformat() if item.updated_at else None
    payload["deal_type"] = deal_type or ("rent" if item.rent_period else "unknown")
    return payload


def submit(listings: list[dict]) -> None:
    body = json.dumps({"listings": listings}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(os.environ["CENTRAL_INGEST_SHARED_SECRET"].encode(), body, hashlib.sha256).hexdigest()
    headers = {"Content-Type":"application/json","X-Signature":signature,"X-Idempotency-Key":str(uuid.uuid4())}
    url = os.environ["CENTRAL_INGEST_URL"].rstrip("/") + "/v1/ingest/listings"
    for attempt in range(5):
        try:
            response = requests.post(url, data=body, headers=headers, timeout=30)
            response.raise_for_status()
            return
        except requests.RequestException:
            if attempt == 4: raise
            time.sleep(2 ** attempt)

