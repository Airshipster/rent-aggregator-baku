import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests
import psycopg
from psycopg.rows import dict_row
from src.utils import image_datetime, parse_dt


QUERY = """
query AuditItems($first:Int,$filter:ItemFilter,$sort:ItemConnectionSort!,$cursor:String){
  itemsConnection(first:$first,after:$cursor,filter:$filter,sort:$sort){
    totalCount
    pageInfo{hasNextPage endCursor}
    edges{node{id updatedAt}}
  }
}
"""


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fetch_recent(session: requests.Session, graphql_url: str, item_filter: dict, cutoff: datetime) -> tuple[int, list[dict]]:
    cursor = None
    recent: list[dict] = []
    total_count = 0
    for _ in range(50):
        response = session.post(
            graphql_url,
            json={
                "query": QUERY,
                "variables": {"first": 100, "filter": item_filter, "sort": "BUMPED_AT_DESC", "cursor": cursor},
            },
            timeout=30,
        )
        response.raise_for_status()
        document = response.json()
        if document.get("errors"):
            raise RuntimeError(document["errors"])
        connection = document["data"]["itemsConnection"]
        total_count = int(connection["totalCount"])
        nodes = [edge["node"] for edge in connection.get("edges") or []]
        recent.extend(node for node in nodes if parse_dt(node["updatedAt"]) >= cutoff)
        if not nodes or min(parse_dt(node["updatedAt"]) for node in nodes) < cutoff:
            break
        page = connection["pageInfo"]
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
    return total_count, recent


def main() -> None:
    base_url = os.getenv("SOURCE_BASE_URL", "https://bina.az").rstrip("/")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    session = requests.Session()
    session.headers.update({"User-Agent": "channel-volume-audit/1.0", "Accept": "application/json"})
    all_nodes: dict[str, dict] = {}
    period_ids: dict[str, list[str]] = {}
    for name, item_filter in (
        ("monthly", {"leased": True, "paidDaily": False, "cityId": 1}),
        ("daily", {"leased": True, "paidDaily": True, "cityId": 1}),
    ):
        total, nodes = fetch_recent(session, f"{base_url}/graphql", item_filter, cutoff)
        period_ids[name] = [str(node["id"]) for node in nodes]
        for node in nodes:
            all_nodes[str(node["id"])] = node
        print(json.dumps({"period": name, "active_total": total, "updated_24h": len(nodes)}, ensure_ascii=False))

    ids = list(all_nodes)
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT source_listing_id,payload,first_seen_at FROM listings WHERE source_listing_id = ANY(%s)",
                (ids,),
            )
            known = {row["source_listing_id"]: row for row in cursor.fetchall()}
            cursor.execute("""SELECT c.created_at,l.payload FROM channel_posts c JOIN listings l ON l.id=c.listing_id""")
            historical = cursor.fetchall()
    apartment_slugs = {"menziller/yeni-tikili", "menziller/kohne-tikili"}
    for name, source_ids in period_ids.items():
        rows = [known[item_id] for item_id in source_ids if item_id in known]
        apartments = [row for row in rows if row["payload"].get("category_slug") in apartment_slugs]
        categories = Counter(row["payload"].get("category_slug") or "unknown" for row in rows)
        previously_known = sum(row["first_seen_at"] < cutoff for row in apartments)
        fresh_photo = sum(
            (image_datetime(row["payload"].get("first_image_url")) or parse_dt(row["payload"].get("updated_at")) or cutoff)
            >= datetime.now(timezone.utc) - timedelta(hours=168)
            for row in apartments
        )
        print(json.dumps({
            "period": name,
            "known_in_database": len(rows),
            "unknown_to_database": len(source_ids) - len(rows),
            "apartments_updated_24h": len(apartments),
            "apartments_known_before_24h": previously_known,
            "apartments_with_photo_under_168h": fresh_photo,
            "categories_24h": categories,
        }, ensure_ascii=False, default=dict))
    print(json.dumps({"unique_rent_items_updated_24h": len(all_nodes), "cutoff": cutoff.isoformat()}, ensure_ascii=False))
    old_policy_pass = 0
    old_policy_fail = 0
    for row in historical:
        payload = row["payload"]
        source_date = image_datetime(payload.get("first_image_url")) or parse_dt(payload.get("updated_at"))
        if source_date is None or source_date >= row["created_at"] - timedelta(hours=168):
            old_policy_pass += 1
        else:
            old_policy_fail += 1
    print(json.dumps({"historical_channel_rows": len(historical), "old_168h_policy_pass": old_policy_pass, "old_168h_policy_fail": old_policy_fail}, ensure_ascii=False))


if __name__ == "__main__":
    main()
