from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ListingSummary:
    listing_id: str
    listing_url: str
    path: str
    updated_at: datetime | None


@dataclass
class ListingDetail:
    listing_id: str
    listing_url: str
    title: str
    price: int | None
    currency: str | None
    rent_period: str
    city: str | None
    district: str | None
    metro: str | None
    landmarks: list[str]
    address_text: str | None
    area_m2: float | None
    rooms: int | None
    floor: int | None
    total_floors: int | None
    repair_status: str | None
    building_type: str | None
    category_slug: str | None
    category_title: str | None
    seller_name: str | None
    seller_type: str
    description_full: str | None
    image_urls: list[str]
    first_image_url: str | None
    google_maps_url: str | None
    latitude: float | None
    longitude: float | None
    updated_at: datetime | None
    source: str = "source"
    is_deleted: bool = False
    raw_status: str | None = None
    has_bill_of_sale: bool | None = None
    has_mortgage: bool | None = None
    land_area_m2: float | None = None


@dataclass
class RunStats:
    found: int = 0
    last_seen_id: str | None = None
    new_count: int = 0
    private_sent: int = 0
    public_sent: int = 0
    errors: int = 0
    skipped_old: int = 0
    updates_sent: int = 0
    messages: list[str] = field(default_factory=list)
