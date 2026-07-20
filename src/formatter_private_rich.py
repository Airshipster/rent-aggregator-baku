from html import escape

from .models import ListingDetail


def format_private_rich(item: ListingDetail, image_urls: list[str]) -> tuple[str, list[dict]]:
    media = [
        {"id": f"p{index + 1}", "media": {"type": "photo", "media": url}}
        for index, url in enumerate(image_urls)
    ]
    html = f"""
    <h3>{escape(title(item))}</h3>
    <table bordered>{table_rows(item)}</table>
    <p>Foto: {len(media)} / {len(item.image_urls)}</p>
    {photo_blocks(len(media))}
    {map_block(item)}
    """
    return html, media


def title(item: ListingDetail) -> str:
    parts = []
    if item.rooms:
        parts.append(f"{item.rooms} otaqlı")
    parts.append(item.building_type or "Mənzil")
    if item.metro or item.district:
        parts.append(item.metro or item.district or "")
    return " · ".join(part for part in parts if part)


def table_rows(item: ListingDetail) -> str:
    rows = [
        ("Qiymət", price(item)),
        ("Ünvan", item.address_text or "Ünvan dəqiqləşdirilir"),
        ("Yaxınlıqda", " · ".join(item.landmarks[:4]) or "Yaxın obyektlər qeyd olunmayıb"),
        ("Parametrlər", specs(item)),
        ("Kirayə verən", seller(item)),
        ("Məlumat", description(item)),
    ]
    return "\n".join(
        f'<tr><th align="right">{escape(label)}</th><th align="left">{escape(value)}</th></tr>'
        for label, value in rows
    )


def price(item: ListingDetail) -> str:
    if item.price is None:
        return "Qiymət göstərilməyib"
    suffix = " / ay" if item.rent_period == "monthly" else " / gün" if item.rent_period == "daily" else ""
    return f"{item.price} {item.currency or 'AZN'}{suffix}"


def specs(item: ListingDetail) -> str:
    parts = []
    if item.rooms:
        parts.append(f"{item.rooms} otaq")
    if item.area_m2 is not None:
        parts.append(f"{item.area_m2:g} m²")
    if item.floor is not None or item.total_floors is not None:
        parts.append(f"{item.floor or '?'}/{item.total_floors or '?'}")
    if item.repair_status:
        parts.append({"var": "təmirli", "yoxdur": "təmirsiz"}.get(item.repair_status, item.repair_status))
    return " · ".join(parts) or "Ətraflı məlumat elanda"


def seller(item: ListingDetail) -> str:
    return "#agentlik" if item.seller_type == "agency" else "#mülkiyyətçi"


def description(item: ListingDetail) -> str:
    text = (item.description_full or "Məlumat əlavə edilməyib").strip()
    if len(text) > 1000:
        return text[:997] + "..."
    return text


def photo_blocks(count: int) -> str:
    return "\n".join(
        "<tg-collage>"
        + "\n".join(f'<img src="tg://photo?id=p{index}"/>' for index in chunk)
        + "</tg-collage>"
        for chunk in balanced_chunks(count)
    )


def balanced_chunks(total: int, max_chunk: int = 10) -> list[list[int]]:
    if total <= 0:
        return []
    parts = (total + max_chunk - 1) // max_chunk
    base = total // parts
    extra = total % parts
    chunks = []
    start = 1
    for index in range(parts):
        size = base + (1 if index < extra else 0)
        end = start + size
        chunks.append(list(range(start, end)))
        start = end
    return chunks


def map_block(item: ListingDetail) -> str:
    if item.latitude is None or item.longitude is None or not item.google_maps_url:
        return ""
    address = escape(item.address_text or "Ünvan dəqiqləşdirilir")
    maps_url = escape(item.google_maps_url)
    return f"""
    <details>
      <summary>Xəritə</summary>
      <p><a href="{maps_url}">Google Xəritə</a></p>
      <figure><tg-map lat="{item.latitude}" long="{item.longitude}" zoom="15"/><figcaption>{address}</figcaption></figure>
    </details>
    """
