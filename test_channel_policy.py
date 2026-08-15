import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

if "server.db" in sys.modules and not hasattr(sys.modules["server.db"], "migrate"):
    sys.modules["server.db"].migrate = None

from server.app import _public_channel_eligible


def image_url(value: datetime) -> str:
    local = value.astimezone(timezone(timedelta(hours=4)))
    return local.strftime("https://example.test/uploads/full/%Y/%m/%d/%H/%M/photo.jpg")


class ChannelPolicyTests(unittest.TestCase):
    def payload(self, photo_date: datetime) -> dict:
        return {
            "channel_candidate": True,
            "deal_type": "rent",
            "city": "Bakı",
            "category_slug": "menziller/yeni-tikili",
            "first_image_url": image_url(photo_date),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    @patch.dict(os.environ, {"ENABLE_PUBLIC_CHANNEL": "true", "MAX_PUBLIC_AGE_HOURS": "168"})
    def test_recent_apartment_is_eligible(self) -> None:
        self.assertTrue(_public_channel_eligible(self.payload(datetime.now(timezone.utc) - timedelta(days=2))))

    @patch.dict(os.environ, {"ENABLE_PUBLIC_CHANNEL": "true", "MAX_PUBLIC_AGE_HOURS": "168"})
    def test_old_bumped_apartment_is_rejected(self) -> None:
        self.assertFalse(_public_channel_eligible(self.payload(datetime.now(timezone.utc) - timedelta(days=8))))

    @patch.dict(os.environ, {"ENABLE_PUBLIC_CHANNEL": "true", "MAX_PUBLIC_AGE_HOURS": "168"})
    def test_non_apartment_is_rejected(self) -> None:
        payload = self.payload(datetime.now(timezone.utc))
        payload["category_slug"] = "heyet-evleri"
        self.assertFalse(_public_channel_eligible(payload))


if __name__ == "__main__":
    unittest.main()
