from html import escape

from .models import ListingDetail


def format_private(item: ListingDetail) -> str:
    lines = [
        f"🏠 <b>{escape(item.title)}</b>",
        f"№ {escape(item.listing_id)}",
        "",
        f"Цена: {fmt_price(item)}",
        f"Аренда: {fmt_period(item.rent_period)}",
        f"Ориентиры: {escape(', '.join(item.landmarks) if item.landmarks else 'не найдены')}",
        f"Район/метро: {escape(' / '.join([x for x in [item.district, item.metro] if x]) or 'не найдено')}",
        f"Адрес: {escape(item.address_text or 'не найден')}",
        f"Площадь: {fmt_area(item)}",
        f"Комнаты: {item.rooms if item.rooms is not None else 'не найдено'}",
        f"Этаж: {fmt_floor(item)}",
        f"Ремонт: {escape(item.repair_status or 'не найдено')}",
        f"Тип здания: {escape(item.building_type or 'не найдено')}",
        f"Продавец: {fmt_seller(item)}",
        "",
        "Описание:",
        escape(item.description_full or "не найдено"),
        "",
        f"Карта: {escape(item.google_maps_url or 'не найдена')}",
        "",
        f"Объявление: {escape(item.listing_url)}",
    ]
    return "\n".join(lines)


def fmt_price(item: ListingDetail) -> str:
    if item.price is None:
        return "не найдена"
    return f"{item.price} {item.currency or ''}".strip()


def fmt_period(value: str) -> str:
    return {"daily": "день", "monthly": "месяц"}.get(value, "неизвестно")


def fmt_area(item: ListingDetail) -> str:
    if item.area_m2 is None:
        return "не найдена"
    return f"{item.area_m2:g} m²"


def fmt_floor(item: ListingDetail) -> str:
    if item.floor is None and item.total_floors is None:
        return "не найден"
    return f"{item.floor or '?'} / {item.total_floors or '?'}"


def fmt_seller(item: ListingDetail) -> str:
    labels = {"owner": "собственник", "agency": "агентство/посредник", "unknown": "неизвестно"}
    name = item.seller_name or "имя не найдено"
    return f"{labels.get(item.seller_type, 'неизвестно')} · {escape(name)}"
