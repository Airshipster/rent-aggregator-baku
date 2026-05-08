import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote, urljoin, urlparse


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_recent(value: datetime | None, hours: int) -> bool:
    if value is None:
        return True
    dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return dt >= now_utc() - timedelta(hours=hours)


def join_url(base: str, path: str) -> str:
    return urljoin(base.rstrip("/") + "/", path.lstrip("/"))


def origin(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def sleep_soft() -> None:
    time.sleep(random.uniform(1.0, 3.0))


def clean_tag(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"[^\wƏəÜüÖöĞğŞşÇçİıА-Яа-я0-9]+", "", value, flags=re.UNICODE)
    return value or None


def detect_challenge(text: str, status_code: int) -> bool:
    if status_code in {403, 429}:
        return True
    lowered = text[:10000].lower()
    markers = ["cf-chl", "captcha", "challenge-platform", "turnstile", "rate limit"]
    return any(marker in lowered for marker in markers)


def image_datetime(url: str | None) -> datetime | None:
    if not url:
        return None
    value = unquote(url)
    match = re.search(r"/uploads/(?:full|f\d+x\d+|thumbnail)/(\d{4})/(\d{2})/(\d{2})/(\d{2})/(\d{2})", value)
    if not match:
        return None
    year, month, day, hour, minute = [int(part) for part in match.groups()]
    return datetime(year, month, day, hour, minute, tzinfo=timezone(timedelta(hours=4)))
