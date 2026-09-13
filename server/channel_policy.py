import os
from src.utils import env_int, image_datetime, is_recent, parse_dt


def public_channel_eligible(payload: dict) -> bool:
    # This legacy freshness proxy is NOT a verified source publication time.
    date = image_datetime(payload.get('first_image_url')) or parse_dt(payload.get('updated_at'))
    return (
        os.getenv('ENABLE_PUBLIC_CHANNEL','false').lower() in {'1','true','yes','on'}
        and not payload.get('is_deleted')
        and payload.get('channel_candidate',True)
        and payload.get('deal_type')=='rent'
        and payload.get('rent_period')=='monthly'
        and payload.get('city')=='Bakı'
        and payload.get('category_slug') in {'menziller/yeni-tikili','menziller/kohne-tikili'}
        and is_recent(date,env_int('MAX_PUBLIC_AGE_HOURS',168))
    )
