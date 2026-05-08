from html import escape

from .models import ListingDetail
from .utils import clean_tag


def format_public(item: ListingDetail) -> str:
    location = " · ".join(item.landmarks[:4]) or item.metro or item.district or "Lokasiya dəqiqləşdirilir"
    lines = [
        f"🏠 <b>{escape(fmt_title(item))}</b>",
        f"💰 {escape(fmt_price(item))} / ay",
        f"📍 {escape(location)}",
        f"📐 {escape(fmt_specs(item))}",
        "",
        escape(" ".join(tags(item))),
        "",
        "🔗 Elana baxmaq:",
        escape(item.listing_url),
    ]
    return "\n".join(lines)


def format_deleted_update(url: str, listing_id: str) -> str:
    return f"❌ Update\nElan silinib və ya artıq aktiv görünmür.\n№ {escape(listing_id)}\n{escape(url)}"


def format_changed_update(item: ListingDetail) -> str:
    return f"🔄 Update\nElan yenilənib.\n№ {escape(item.listing_id)}\n{escape(item.listing_url)}"


def fmt_price(item: ListingDetail) -> str:
    if item.price is None:
        return "Qiymət göstərilməyib"
    return f"{item.price} {item.currency or 'AZN'}".strip()


def fmt_title(item: ListingDetail) -> str:
    rooms = f"{item.rooms} otaqlı" if item.rooms else "Mənzil"
    seller = {"owner": "mülkiyyətçi", "agency": "agentlik", "unknown": "naməlum"}.get(item.seller_type, "naməlum")
    return f"{rooms} mənzil · #{seller}"


def fmt_specs(item: ListingDetail) -> str:
    area = f"{item.area_m2:g} m²" if item.area_m2 is not None else "? m²"
    floors = f"{item.floor or '?'}/{item.total_floors or '?'}"
    repair = fmt_repair(item.repair_status or "")
    return f"{area} · {floors} · {repair}"


def fmt_repair(value: str) -> str:
    return {"var": "təmirli", "yoxdur": "təmirsiz"}.get(value, value or "təmir qeyd olunmayıb")


def tags(item: ListingDetail) -> list[str]:
    result = []
    district = clean_tag((item.district or item.metro or "").replace(" r.", "").replace(" m.", ""))
    if district:
        result.append(f"#{district}")
    if item.rooms:
        result.append(f"#{item.rooms}otaq")
    return result[:3]
