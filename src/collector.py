import json
import os
from pathlib import Path

from .central_ingest import listing_payload, submit
from .source_client import SourceClient
from .source_parser import SourceParser
from .utils import env_int, sleep_soft


def filters() -> list[dict]:
    # Empty category restrictions intentionally collect every property category in Baku.
    raw = os.getenv("COLLECTOR_FILTERS_JSON", '[{"leased":true,"cityId":1},{"leased":false,"cityId":1}]')
    value = json.loads(raw)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("COLLECTOR_FILTERS_JSON must be a JSON array of source filters")
    return value


STATE_PATH = Path("state/central_collector.json")


def load_seen() -> list[str]:
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return [str(item) for item in value.get("seen_listing_ids", [])]
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return []


def save_seen(values: list[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"seen_listing_ids": values[-5000:]}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = SourceParser(SourceClient())
    parser.client.get_start_page()
    batches, known = [], set()
    for item_filter in filters():
        batch = []
        for summary in parser.list_recent(env_int("MAX_LISTINGS_PER_RUN", 100), pages=env_int("LIST_PAGES_PER_RUN", 3), item_filter=item_filter):
            if summary.listing_id not in known:
                known.add(summary.listing_id); batch.append((summary, item_filter))
        batches.append(batch)
    seen_order = load_seen()
    seen = set(seen_order)
    candidates = []
    while any(batches) and len(candidates) < env_int("MAX_DETAIL_FETCHES_PER_RUN", 100):
        for batch in batches:
            while batch and batch[0][0].listing_id in seen:
                batch.pop(0)
            if batch and len(candidates) < env_int("MAX_DETAIL_FETCHES_PER_RUN", 100):
                candidates.append(batch.pop(0))
    details = []
    submitted_ids = []
    for summary, item_filter in candidates:
        sleep_soft()
        detail = parser.get_detail(summary.listing_id)
        if detail:
            details.append(listing_payload(detail, "rent" if item_filter.get("leased") else "sale"))
            submitted_ids.append(summary.listing_id)
    submit(details)
    save_seen(seen_order + submitted_ids)
    print(f"collected={len(details)}")


if __name__ == "__main__": main()
