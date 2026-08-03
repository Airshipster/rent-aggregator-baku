from html import escape

from .models import ListingDetail


LABELS = {
    "ru": {"price":"Цена", "address":"Адрес", "near":"Рядом", "specs":"Параметры", "seller":"Разместил", "info":"Информация", "photos":"Фото", "map":"Карта", "maps":"Google Карты", "unknown_address":"Адрес не указан", "unknown_near":"Ориентиры не указаны", "unknown_price":"Цена не указана", "details":"Подробнее в объявлении", "no_info":"Информация не добавлена", "room":"комн.", "renovated":"с ремонтом", "not_renovated":"без ремонта", "month":"мес.", "day":"день", "new":"Новостройка", "old":"Вторичка", "apartment":"квартира", "house":"дом / дача", "office":"офис", "garage":"гараж", "land":"земельный участок", "commercial":"коммерческий объект", "floor_word":"эт."},
    "az": {"price":"Qiymət", "address":"Ünvan", "near":"Yaxınlıqda", "specs":"Parametrlər", "seller":"Elanı yerləşdirən", "info":"Məlumat", "photos":"Foto", "map":"Xəritə", "maps":"Google Xəritə", "unknown_address":"Ünvan dəqiqləşdirilir", "unknown_near":"Yaxın obyektlər qeyd olunmayıb", "unknown_price":"Qiymət göstərilməyib", "details":"Ətraflı məlumat elanda", "no_info":"Məlumat əlavə edilməyib", "room":"otaq", "renovated":"təmirli", "not_renovated":"təmirsiz", "month":"ay", "day":"gün", "new":"Yeni tikili", "old":"Köhnə tikili", "apartment":"mənzil", "house":"həyət evi / bağ evi", "office":"ofis", "garage":"qaraj", "land":"torpaq sahəsi", "commercial":"obyekt", "floor_word":"mərtəbə"},
    "en": {"price":"Price", "address":"Address", "near":"Nearby", "specs":"Details", "seller":"Posted by", "info":"Information", "photos":"Photos", "map":"Map", "maps":"Google Maps", "unknown_address":"Address not specified", "unknown_near":"Nearby places not specified", "unknown_price":"Price not specified", "details":"See listing for details", "no_info":"No information provided", "room":"rooms", "renovated":"renovated", "not_renovated":"not renovated", "month":"month", "day":"day", "new":"New building", "old":"Resale", "apartment":"apartment", "house":"house / cottage", "office":"office", "garage":"garage", "land":"land plot", "commercial":"commercial property", "floor_word":"floors"},
}


def label(language: str, key: str) -> str:
    return LABELS.get(language, LABELS["ru"])[key]


def format_private_rich(item: ListingDetail, image_urls: list[str], language: str = "az") -> tuple[str, list[dict]]:
    media = [
        {"id": f"p{index + 1}", "media": {"type": "photo", "media": url}}
        for index, url in enumerate(image_urls)
    ]
    html = f"""
    <p><b>{escape(title(item, language))}</b></p>
    <table bordered>{table_rows(item, language)}</table>
    <p>{label(language, "photos")}: {len(media)} / {len(item.image_urls)}</p>
    {photo_blocks(len(media))}
    {map_block(item, language)}
    """
    return html, media


def title(item: ListingDetail, language: str = "az") -> str:
    slug = item.category_slug or ""
    parts = []
    if slug.startswith("menziller/"):
        if item.rooms:
            room = {"ru":f"{item.rooms}-комнатная", "az":f"{item.rooms} otaqlı", "en":f"{item.rooms}-room"}.get(language, f"{item.rooms}-room")
            parts.append(f"{room} {label(language, 'apartment')}")
        else:
            parts.append(label(language, "apartment"))
        parts.append(label(language, "new" if slug.endswith("yeni-tikili") else "old"))
    elif slug == "heyet-evleri":
        if item.rooms:
            prefix={"ru":f"{item.rooms}-комнатный ","az":f"{item.rooms} otaqlı ","en":f"{item.rooms}-room "}.get(language,f"{item.rooms}-room ")
        else:
            prefix=""
        parts.append(prefix + label(language, "house"))
        if item.total_floors:
            parts.append(f"{item.total_floors} {label(language, 'floor_word')}")
    else:
        kind = {"ofisler":"office", "qarajlar":"garage", "torpaq":"land", "obyektler":"commercial"}.get(slug, "commercial")
        area = item.land_area_m2 if slug == "torpaq" else item.area_m2
        if area is not None:
            unit = "sot" if slug == "torpaq" else "m²"
            parts.append(f"{area:g} {unit}")
        parts.append(label(language, kind))
    if item.metro or item.district:
        parts.append(item.metro or item.district or "")
    return " · ".join(part for part in parts if part)


def table_rows(item: ListingDetail, language: str = "az") -> str:
    rows = [
        (label(language, "price"), price(item, language)),
        (label(language, "address"), item.address_text or label(language, "unknown_address")),
        (label(language, "near"), " · ".join(item.landmarks[:4]) or label(language, "unknown_near")),
        (label(language, "specs"), specs(item, language)),
        (label(language, "seller"), seller(item)),
        (label(language, "info"), description(item, language)),
    ]
    return "\n".join(
        f'<tr><th align="right">{escape(label)}</th><th align="left">{escape(value)}</th></tr>'
        for label, value in rows
    )


def price(item: ListingDetail, language: str = "az") -> str:
    if item.price is None:
        return label(language, "unknown_price")
    suffix = f" / {label(language, 'month')}" if item.rent_period == "monthly" else f" / {label(language, 'day')}" if item.rent_period == "daily" else ""
    return f"{item.price} {item.currency or 'AZN'}{suffix}"


def specs(item: ListingDetail, language: str = "az") -> str:
    parts = []
    if item.rooms:
        parts.append(f"{item.rooms} {label(language, 'room')}")
    if item.area_m2 is not None:
        parts.append(f"{item.area_m2:g} m²")
    if item.floor is not None or item.total_floors is not None:
        parts.append(f"{item.floor or '?'}/{item.total_floors or '?'}")
    if item.repair_status:
        parts.append({"var": label(language, "renovated"), "yoxdur": label(language, "not_renovated")}.get(item.repair_status, item.repair_status))
    return " · ".join(parts) or label(language, "details")


def seller(item: ListingDetail) -> str:
    return "#agentlik" if item.seller_type == "agency" else "#mülkiyyətçi"


def description(item: ListingDetail, language: str = "az") -> str:
    text = (item.description_full or "").strip()
    normalized = text.lower()
    meaningful = normalized.strip(" \t\r\n.!?,;:-_—–•")
    placeholders = {
        "aciqlama yoxdur",
        "açıqlama yoxdur",
        "melumat yoxdur",
        "məlumat yoxdur",
        "serh yoxdur",
        "şərh yoxdur",
    }
    if not meaningful or normalized in placeholders:
        return label(language, "no_info")
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


def map_block(item: ListingDetail, language: str = "az") -> str:
    if item.latitude is None or item.longitude is None or not item.google_maps_url:
        return ""
    address = escape(item.address_text or label(language, "unknown_address"))
    maps_url = escape(item.google_maps_url)
    return f"""
    <details>
      <summary>{label(language, "map")}</summary>
      <p><a href="{maps_url}">{label(language, "maps")}</a></p>
      <figure><tg-map lat="{item.latitude}" long="{item.longitude}" zoom="15"/><figcaption>{address}</figcaption></figure>
    </details>
    """
