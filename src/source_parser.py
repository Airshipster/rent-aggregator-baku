from typing import Any

from .models import ListingDetail, ListingSummary
from .source_client import SourceClient
from .utils import join_url, parse_dt


SEARCH_QUERY = """
query SearchItems($first:Int,$filter:ItemFilter,$sort:ItemConnectionSort!,$cursor:String){
  itemsConnection(first:$first,after:$cursor,filter:$filter,sort:$sort){
    totalCount
    pageInfo{hasNextPage endCursor}
    edges{
      node{
        id
        path
        updatedAt
      }
    }
  }
}
"""


DETAIL_QUERY = """
query ItemDetail($id:ID!){
  item(id:$id){
    id
    path
    address
    description
    leased
    rooms
    floor
    floors
    hasRepair
    contactName
    contactTypeName
    buildingTypeName
    longitude
    latitude
    updatedAt
    expiresAt
    isExpiredManually
    location{fullName path}
    nearestLocations{
      ... on Location{id fullName path}
      ... on City{id name path}
    }
    area{value units}
    landArea{value units}
    price{total currency perAre}
    paidDaily
    company{id name targetType}
    business{
      ... on Agency{id name path itemsCount viewsCount contactAddress latitude longitude city{name}}
      ... on Residence{id companyName path address lat lng city{name}}
    }
    category{id name pluralName slug title}
    city{id name path slug}
    photos{full f660x496 thumbnail}
  }
}
"""


class SourceParser:
    def __init__(self, client: SourceClient) -> None:
        self.client = client

    def list_recent(self, limit: int, pages: int = 1) -> list[ListingSummary]:
        items: list[ListingSummary] = []
        cursor = None
        for _ in range(max(1, pages)):
            data = self.client.graphql(
                SEARCH_QUERY,
                {
                    "first": limit,
                    "filter": {"leased": True, "cityId": 1},
                    "sort": "BUMPED_AT_DESC",
                    "cursor": cursor,
                },
            )
            connection = data["itemsConnection"]
            for edge in connection.get("edges") or []:
                node = edge.get("node") or {}
                listing_id = str(node.get("id") or "")
                path = node.get("path") or f"/items/{listing_id}"
                if listing_id:
                    items.append(
                        ListingSummary(
                            listing_id=listing_id,
                            listing_url=join_url(self.client.base_url, path),
                            path=path,
                            updated_at=parse_dt(node.get("updatedAt")),
                        )
                    )
            page_info = connection.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
        return items

    def get_detail(self, listing_id: str) -> ListingDetail | None:
        data = self.client.graphql(DETAIL_QUERY, {"id": listing_id})
        node = data.get("item")
        if not node:
            return None
        return self._detail_from_node(node)

    def check_exists(self, listing_id: str) -> bool:
        data = self.client.graphql("query ItemCheck($id:ID!){item(id:$id){id isExpiredManually}}", {"id": listing_id})
        item = data.get("item")
        return bool(item and not item.get("isExpiredManually"))

    def _detail_from_node(self, node: dict[str, Any]) -> ListingDetail:
        listing_id = str(node.get("id") or "")
        path = node.get("path") or f"/items/{listing_id}"
        price = node.get("price") or {}
        area = node.get("area") or {}
        city = node.get("city") or {}
        location = node.get("location") or {}
        category = node.get("category") or {}
        photos = node.get("photos") or []
        image_urls = [p.get("full") or p.get("f660x496") or p.get("thumbnail") for p in photos]
        image_urls = [url for url in image_urls if url]
        landmarks = self._landmarks(node)
        seller_type = self._seller_type(node)
        latitude = node.get("latitude")
        longitude = node.get("longitude")
        maps_url = f"https://www.google.com/maps?q={latitude},{longitude}" if latitude and longitude else None
        return ListingDetail(
            listing_id=listing_id,
            listing_url=join_url(self.client.base_url, path),
            title=self._title(node),
            price=price.get("total"),
            currency=price.get("currency"),
            rent_period="daily" if node.get("paidDaily") else "monthly",
            city=city.get("name"),
            district=self._district(landmarks),
            metro=self._metro(landmarks, location.get("fullName")),
            landmarks=landmarks,
            address_text=node.get("address"),
            area_m2=area.get("value"),
            rooms=node.get("rooms"),
            floor=node.get("floor"),
            total_floors=node.get("floors"),
            repair_status=self._repair(node.get("hasRepair")),
            building_type=node.get("buildingTypeName") or category.get("name"),
            category_slug=category.get("slug"),
            category_title=category.get("title"),
            seller_name=node.get("contactName"),
            seller_type=seller_type,
            description_full=node.get("description"),
            image_urls=image_urls,
            first_image_url=image_urls[0] if image_urls else None,
            google_maps_url=maps_url,
            latitude=latitude,
            longitude=longitude,
            updated_at=parse_dt(node.get("updatedAt")),
            is_deleted=bool(node.get("isExpiredManually")),
            raw_status="expired" if node.get("isExpiredManually") else None,
        )

    def _landmarks(self, node: dict[str, Any]) -> list[str]:
        values: list[str] = []
        location = (node.get("location") or {}).get("fullName")
        if location:
            values.append(location.strip())
        for item in node.get("nearestLocations") or []:
            value = item.get("fullName") or item.get("name")
            if value and value.strip() not in values:
                values.append(value.strip())
        return values

    def _district(self, landmarks: list[str]) -> str | None:
        for value in landmarks:
            if value.endswith("r."):
                return value
        return None

    def _metro(self, landmarks: list[str], location: str | None) -> str | None:
        candidates = landmarks + ([location] if location else [])
        for value in candidates:
            if value and value.endswith("m."):
                return value
        return None

    def _seller_type(self, node: dict[str, Any]) -> str:
        text = " ".join(str(x or "").lower() for x in [node.get("contactTypeName"), (node.get("company") or {}).get("targetType")])
        if "owner" in text or "mülkiyyət" in text or "sahib" in text:
            return "owner"
        if "agency" in text or "agent" in text or "vasitə" in text:
            return "agency"
        if node.get("business"):
            return "agency"
        return "unknown"

    def _repair(self, value: Any) -> str | None:
        if value is True:
            return "var"
        if value is False:
            return "yoxdur"
        return None

    def _title(self, node: dict[str, Any]) -> str:
        rooms = node.get("rooms")
        category = (node.get("category") or {}).get("name") or "Mənzil"
        location = (node.get("location") or {}).get("fullName")
        parts = []
        if rooms:
            parts.append(f"{rooms} otaqlı")
        parts.append(category)
        if location:
            parts.append(location)
        return " · ".join(parts)
