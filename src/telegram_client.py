import json
import os
import tempfile
from pathlib import Path
from typing import Any

import requests

from .utils import env_bool, env_int


class TelegramClient:
    def __init__(self) -> None:
        self.token = os.environ["TELEGRAM_BOT_TOKEN"]
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.timeout = env_int("REQUEST_TIMEOUT_SECONDS", 20)
        self.protect = env_bool("PROTECT_PRIVATE_CONTENT", True)
        self.session = requests.Session()

    def call(self, method: str, payload: dict[str, Any] | None = None, files: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.post(
            f"{self.base_url}/{method}",
            data=payload if files else None,
            json=payload if not files else None,
            files=files,
            timeout=self.timeout,
        )
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"telegram {method} failed: {data.get('description')}")
        return data["result"]

    def get_chat(self, chat_id: str) -> dict[str, Any]:
        return self.call("getChat", {"chat_id": chat_id})

    def send_message(
        self,
        chat_id: str,
        text: str,
        protect_content: bool = False,
        link_preview_url: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        if protect_content:
            payload["protect_content"] = True
        if link_preview_url:
            payload["link_preview_options"] = {"url": link_preview_url, "prefer_large_media": True}
        return self.call("sendMessage", payload)

    def send_long_message(self, chat_id: str, text: str, protect_content: bool = False) -> list[dict[str, Any]]:
        chunks = []
        current = ""
        for line in text.splitlines():
            candidate = f"{current}\n{line}" if current else line
            if len(candidate) > 3800:
                chunks.append(current)
                current = line
            else:
                current = candidate
        if current:
            chunks.append(current)
        return [self.send_message(chat_id, chunk, protect_content=protect_content) for chunk in chunks]

    def edit_message(self, chat_id: str, message_id: int, text: str) -> dict[str, Any]:
        return self.call("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text})

    def pin_message(self, chat_id: str, message_id: int) -> None:
        self.call("pinChatMessage", {"chat_id": chat_id, "message_id": message_id, "disable_notification": True})

    def send_location(self, chat_id: str, latitude: float, longitude: float, protect_content: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "latitude": latitude, "longitude": longitude}
        if protect_content:
            payload["protect_content"] = True
        return self.call("sendLocation", payload)

    def send_photo_url(self, chat_id: str, url: str, protect_content: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "photo": url}
        if protect_content:
            payload["protect_content"] = True
        return self.call("sendPhoto", payload)

    def send_photo_file(self, chat_id: str, path: Path, protect_content: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id}
        if protect_content:
            payload["protect_content"] = "true"
        with path.open("rb") as handle:
            return self.call("sendPhoto", payload, files={"photo": handle})

    def send_media_group_urls(self, chat_id: str, urls: list[str], protect_content: bool = False) -> dict[str, Any]:
        media = [{"type": "photo", "media": url} for url in urls]
        payload: dict[str, Any] = {"chat_id": chat_id, "media": json.dumps(media)}
        if protect_content:
            payload["protect_content"] = "true"
        return self.call("sendMediaGroup", payload)

    def send_media_group_files(self, chat_id: str, paths: list[Path], protect_content: bool = False) -> dict[str, Any]:
        media = []
        files = {}
        handles = []
        try:
            for index, path in enumerate(paths):
                key = f"photo{index}"
                media.append({"type": "photo", "media": f"attach://{key}"})
                handle = path.open("rb")
                handles.append(handle)
                files[key] = handle
            payload: dict[str, Any] = {"chat_id": chat_id, "media": json.dumps(media)}
            if protect_content:
                payload["protect_content"] = "true"
            return self.call("sendMediaGroup", payload, files=files)
        finally:
            for handle in handles:
                handle.close()

    def send_photos(self, chat_id: str, urls: list[str], listing_id: str, max_images: int) -> int:
        sent = 0
        urls = urls[:max_images]
        for start in range(0, len(urls), 10):
            chunk = urls[start : start + 10]
            if start >= 10:
                self.send_message(chat_id, f"Продолжение фотографий к объявлению №{listing_id}", protect_content=self.protect)
            if len(chunk) == 1:
                self._send_one_photo(chat_id, chunk[0])
                sent += 1
            else:
                self._send_group(chat_id, chunk)
                sent += len(chunk)
        return sent

    def _send_one_photo(self, chat_id: str, url: str) -> None:
        try:
            self.send_photo_url(chat_id, url, protect_content=self.protect)
        except Exception:
            path = self._download_temp(url)
            try:
                self.send_photo_file(chat_id, path, protect_content=self.protect)
            finally:
                path.unlink(missing_ok=True)

    def _send_group(self, chat_id: str, urls: list[str]) -> None:
        try:
            self.send_media_group_urls(chat_id, urls, protect_content=self.protect)
        except Exception:
            paths = [self._download_temp(url) for url in urls]
            try:
                self.send_media_group_files(chat_id, paths, protect_content=self.protect)
            finally:
                for path in paths:
                    path.unlink(missing_ok=True)

    def _download_temp(self, url: str) -> Path:
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        suffix = ".jpg"
        fd, name = tempfile.mkstemp(prefix="rent_", suffix=suffix)
        path = Path(name)
        with os.fdopen(fd, "wb") as handle:
            handle.write(response.content)
        return path

    def get_updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": 0, "allowed_updates": ["message", "my_chat_member"]}
        if offset:
            payload["offset"] = offset
        return self.call("getUpdates", payload)

    def leave_chat(self, chat_id: str) -> None:
        self.call("leaveChat", {"chat_id": chat_id})

    def delete_message(self, chat_id: str, message_id: int) -> None:
        self.call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    def unpin_message(self, chat_id: str, message_id: int) -> None:
        self.call("unpinChatMessage", {"chat_id": chat_id, "message_id": message_id})
