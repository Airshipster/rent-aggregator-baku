"""Strict, locale-aware numeric ranges; ambiguous input is never guessed."""
import re
from decimal import Decimal, InvalidOperation


FIELDS = {'price', 'rooms', 'area_m2', 'land_area_m2', 'floor', 'total_floors'}


def number(text: str, integer: bool = False) -> float | int:
    text = text.strip().replace('\u00a0', ' ').replace('\u202f', ' ')
    if ' ' in text:
        if not re.fullmatch(r'\d{1,3}(?: \d{3})+(?:[.,]\d{1,2})?', text):
            raise ValueError('invalid grouping')
        text = text.replace(' ', '')
    if not re.fullmatch(r'\d+(?:[.,]\d{1,2})?', text):
        raise ValueError('ambiguous or invalid number')
    try:
        value = Decimal(text.replace(',', '.'))
    except InvalidOperation as exc:
        raise ValueError('invalid number') from exc
    if not value.is_finite() or value <= 0 or value > 10**12:
        raise ValueError('number out of bounds')
    if integer and value != value.to_integral_value():
        raise ValueError('whole number required')
    return int(value) if integer else float(value)


def parse_range(text: str, field: str) -> tuple[float | int | None, float | int | None]:
    if field not in FIELDS:
        raise ValueError('unknown range')
    value = text.strip().lower()
    if value in {'any', 'неважно', 'любой', 'все', 'istənilən', 'hamısı'}:
        return None, None
    integer = field in {'rooms', 'floor', 'total_floors'}
    units = {
        'price': r'(?:azn|manat|манат|₼)',
        'rooms': r'(?:rooms?|комнат[аы]?|otaq)',
        'floor': r'(?:floors?|этаж(?:а|ей)?|mərtəbə)',
        'total_floors': r'(?:floors?|этаж(?:а|ей)?|mərtəbə)',
        'area_m2': r'(?:m2|m²|м2|м²|кв\.?\s*м)',
        'land_area_m2': r'(?:sot|сот(?:ка|ки|ок)?)',
    }
    value = re.sub(units[field], '', value).strip()
    low = re.fullmatch(r'(?:от|from|minimum|min)\s+(.+)', value)
    high = re.fullmatch(r'(?:до|up to|maximum|max)\s+(.+)', value)
    pair = re.fullmatch(r'(?:(?:с|от|from)\s+)?(.+?)\s*(?:-|–|—|\bпо\b|\bдо\b|\bto\b|\bilə\b)\s*(.+)', value)
    if pair:
        bounds = number(pair[1], integer), number(pair[2], integer)
    elif low:
        bounds = number(low[1], integer), None
    elif high:
        bounds = None, number(high[1], integer)
    elif value.endswith('+'):
        bounds = number(value[:-1], integer), None
    else:
        exact = number(value, integer)
        bounds = exact, exact
    if bounds[0] is not None and bounds[1] is not None and bounds[0] > bounds[1]:
        raise ValueError('minimum exceeds maximum')
    # Legacy payloads use this key for the source's sot value. Do not silently
    # change its unit without a versioned parser/data migration.
    return bounds
