import re


def redact_error(value: object) -> str:
    text = re.sub(r'\d{6,}:[A-Za-z0-9_-]{20,}', '[REDACTED]', str(value))
    return re.sub(r'https?://\S+', '[URL]', text)[:500]


class TelegramAPIError(RuntimeError):
    def __init__(self, data: dict):
        self.code = data.get('error_code')
        self.retry_after = (data.get('parameters') or {}).get('retry_after')
        super().__init__(redact_error(data.get('description', 'Telegram API error')))
