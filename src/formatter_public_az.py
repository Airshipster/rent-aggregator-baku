from html import escape

from .models import ListingDetail
from .utils import clean_tag


def format_public(item: ListingDetail) -> str:
    location = ", ".join(item.landmarks[:4]) or item.district or item.metro or item.address_text or "Lokasiya dəqiqləşdirilir"
    lines = [
        "🏠 <b>Kirayə mənzil</b>",
        f"💰 {escape(fmt_price(item))}",
        f"📍 {escape(location)}",
        f"📐 {escape(fmt_specs(item))}",
    ]
    if item.repair_status:
        lines.append(f"🛠 {escape(fmt_repair(item.repair_status))}")
    lines.extend(["", escape(" ".join(tags(item))), "", "Elan:", escape(item.listing_url)])
    return "\n".join(lines)


def format_deleted_update(url: str, listing_id: str) -> str:
    return f"❌ Update\nElan silinib və ya artıq aktiv görünmür.\n№ {escape(listing_id)}\n{escape(url)}"


def format_changed_update(item: ListingDetail) -> str:
    return f"🔄 Update\nElan yenilənib.\n№ {escape(item.listing_id)}\n{escape(item.listing_url)}"


def fmt_price(item: ListingDetail) -> str:
    if item.price is None:
        return "Qiymət göstərilməyib"
    return f"{item.price} {item.currency or ''}".strip()


def fmt_specs(item: ListingDetail) -> str:
    area = f"{item.area_m2:g} m²" if item.area_m2 is not None else "? m²"
    rooms = f"{item.rooms} otaq" if item.rooms is not None else "? otaq"
    floors = f"{item.floor or '?'}/{item.total_floors or '?'} mərtəbə"
    return f"{area} · {rooms} · {floors}"


def fmt_repair(value: str) -> str:
    return {"var": "təmirli", "yoxdur": "təmirsiz"}.get(value, value)


def tags(item: ListingDetail) -> list[str]:
    result = []
    seller = {"owner": "mülkiyyətçi", "agency": "agentlik", "unknown": "naməlum"}.get(item.seller_type, "naməlum")
    district = clean_tag((item.district or item.metro or "").replace(" r.", "").replace(" m.", ""))
    if district:
        result.append(f"#{district}")
    if item.rooms:
        result.append(f"#{item.rooms}otaq")
    result.append("#kirayə")
    result.append(f"#{seller}")
    return result[:7]
