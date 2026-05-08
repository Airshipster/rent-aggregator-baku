import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .telegram_client import TelegramClient


DEFAULT_STATE = {
    "last_seen_listing_id": None,
    "last_seen_listing_url": None,
    "updated_at": None,
    "paused": False,
    "update_offset": None,
    "recent_listings": [],
    "deleted_notified_ids": [],
    "last_update_check_at": None,
}


class StateStore:
    def __init__(self, telegram: TelegramClient | None = None) -> None:
        self.telegram = telegram
        self.chat_id = os.getenv("TELEGRAM_STATE_CHAT_ID")
        self.fallback_path = Path(os.getenv("STATE_FALLBACK_FILE", "state/last_seen.json"))
        self.message_id: int | None = None

    def load(self) -> dict[str, Any]:
        state = dict(DEFAULT_STATE)
        loaded = None
        if self.telegram and self.chat_id:
            loaded = self._load_telegram()
        if loaded is None:
            loaded = self._load_file()
        if loaded:
            state.update(loaded)
        return state

    def save(self, state: dict[str, Any]) -> None:
        state = self._compact(state)
        if self.telegram and self.chat_id:
            self._save_telegram(state)
        else:
            self._save_file(state)

    def _load_telegram(self) -> dict[str, Any] | None:
        chat = self.telegram.get_chat(self.chat_id)
        pinned = chat.get("pinned_message")
        if not pinned:
            return None
        text = pinned.get("text") or ""
        self.message_id = pinned.get("message_id")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _save_telegram(self, state: dict[str, Any]) -> None:
        text = json.dumps(state, ensure_ascii=False, indent=2)
        if self.message_id:
            try:
                self.telegram.edit_message(self.chat_id, self.message_id, text)
                return
            except Exception:
                pass
        message = self.telegram.send_message(self.chat_id, text)
        self.message_id = message["message_id"]
        self.telegram.pin_message(self.chat_id, self.message_id)

    def _load_file(self) -> dict[str, Any] | None:
        if not self.fallback_path.exists():
            return None
        return json.loads(self.fallback_path.read_text(encoding="utf-8"))

    def _save_file(self, state: dict[str, Any]) -> None:
        self.fallback_path.parent.mkdir(parents=True, exist_ok=True)
        self.fallback_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def _compact(self, state: dict[str, Any]) -> dict[str, Any]:
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        state["recent_listings"] = list((state.get("recent_listings") or [])[-100:])
        state["deleted_notified_ids"] = list((state.get("deleted_notified_ids") or [])[-100:])
        return state
