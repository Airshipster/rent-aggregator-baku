from typing import Any


def _value(payload: dict[str, Any], field: str) -> Any:
    return payload.get(field)


def _matches_basic(payload: dict[str, Any], basic: dict[str, Any]) -> bool:
    for field in ("deal_type", "category_slug", "city", "district", "rent_period", "currency"):
        choices = basic.get(field)
        if choices and _value(payload, field) not in choices:
            return False
    for field in ("price", "area_m2", "rooms"):
        value = _value(payload, field)
        minimum, maximum = basic.get(f"{field}_min"), basic.get(f"{field}_max")
        if value is not None and minimum is not None and value < minimum:
            return False
        if value is not None and maximum is not None and value > maximum:
            return False
    return True


def matches(payload: dict[str, Any], basic: dict[str, Any], additional: dict[str, Any]) -> bool:
    if not _matches_basic(payload, basic):
        return False
    # Optional values are inclusive when missing. strict is deliberately per field.
    for field, rule in additional.items():
        if not isinstance(rule, dict) or not rule.get("values"):
            continue
        value, values = _value(payload, field), set(rule["values"])
        if value is None:
            if rule.get("strict"):
                return False
        elif isinstance(value, list):
            if not values.intersection(value):
                return False
        elif value not in values:
            return False
    return True
