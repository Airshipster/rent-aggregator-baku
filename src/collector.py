import json
import os
from pathlib import Path

from .central_ingest import listing_payload, submit
from .source_client import SourceClient
from .source_parser import SourceParser
from .utils import env_int, is_recent, sleep_soft


def filters() -> list[dict]:
    # Empty city/category restrictions cover the national recent feed. Rotating city
    # filters below prevent less active cities from being hidden by Baku listings.
    raw = os.getenv(
        "COLLECTOR_FILTERS_JSON",
        '[{"leased":true,"paidDaily":false},{"leased":true,"paidDaily":true},{"leased":false}]',
    )
    value = json.loads(raw)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError("COLLECTOR_FILTERS_JSON must be a JSON array of source filters")
    return value


STATE_PATH = Path("state/central_collector.json")


def load_state() -> dict:
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return {
            "seen_listing_ids": [str(item) for item in value.get("seen_listing_ids", [])],
            "city_cursor": int(value.get("city_cursor") or 0),
        }
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return {"seen_listing_ids": [], "city_cursor": 0}


def save_state(values: list[str], city_cursor: int) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"seen_listing_ids": values[-5000:], "city_cursor": city_cursor}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = SourceParser(SourceClient())
    parser.client.get_start_page()
    state = load_state()
    base_filters = filters()
    cities = parser.list_cities()
    batch_size = max(1, env_int("COLLECTOR_CITY_BATCH_SIZE", 5))
    cursor = state["city_cursor"] % max(1, len(cities))
    city_batch = (cities + cities)[cursor:cursor + min(batch_size, len(cities))]
    expanded_filters = list(base_filters)
    for city_id, _city_name in city_batch:
        expanded_filters.extend([{**item, "cityId": city_id} for item in base_filters if "cityId" not in item])
    batches, known = [], set()
    for item_filter in expanded_filters:
        batch = []
        for summary in parser.list_recent(env_int("MAX_LISTINGS_PER_RUN", 100), pages=env_int("LIST_PAGES_PER_RUN", 3), item_filter=item_filter):
            if summary.listing_id not in known and is_recent(summary.updated_at, env_int("MAX_NEW_AGE_HOURS", 24)):
                known.add(summary.listing_id); batch.append((summary, item_filter))
        batches.append(batch)
    seen_order = state["seen_listing_ids"]
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
        try:
            detail = parser.get_detail(summary.listing_id)
            if detail:
                deal_type = "rent" if item_filter.get("leased") else "sale"
                payload = listing_payload(detail, deal_type)
                payload["rent_period"] = (
                    "daily" if item_filter.get("paidDaily") else "monthly" if deal_type == "rent" else None
                )
                details.append(payload)
                submitted_ids.append(summary.listing_id)
        except Exception as exc:
            print(f"detail_error={summary.listing_id}:{type(exc).__name__}")
    submit(details)
    next_cursor = (cursor + len(city_batch)) % max(1, len(cities))
    save_state(seen_order + submitted_ids, next_cursor)
    print(f"collected={len(details)} city_batch={','.join(str(item[0]) for item in city_batch)} next_city_cursor={next_cursor}")


if __name__ == "__main__": main()
