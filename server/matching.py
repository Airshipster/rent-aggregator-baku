from typing import Any


def _value(payload: dict[str, Any], field: str) -> Any:
    return payload.get(field)


def _matches_basic(payload: dict[str, Any], basic: dict[str, Any]) -> bool:
    for field in ("deal_type", "category_slug", "city", "district", "rent_period", "currency"):
        choices = basic.get(field)
        if choices and _value(payload, field) not in choices:
            return False
    for field in ("price", "area_m2", "land_area_m2", "rooms"):
        value = _value(payload, field)
        minimum, maximum = basic.get(f"{field}_min"), basic.get(f"{field}_max")
        if value is None and (minimum is not None or maximum is not None):
            return False
        if value is not None and minimum is not None and value < minimum:
            return False
        if value is not None and maximum is not None and value > maximum:
            return False
    return True


def matches(payload: dict[str, Any], basic: dict[str, Any], additional: dict[str, Any]) -> bool:
    if not _matches_basic(payload, basic):
        return False
    # Optional values explicitly model whether an unknown source value is accepted.
    for field, rule in additional.items():
        if not isinstance(rule, dict) or ("values" not in rule and "include_unknown" not in rule):
            continue
        value, values = _value(payload, field), set(rule["values"])
        if value is None or value == "unknown":
            if not rule.get("include_unknown", not rule.get("strict", False)):
                return False
        elif isinstance(value, list):
            if not values.intersection(value):
                return False
        elif value not in values:
            return False
    return True
