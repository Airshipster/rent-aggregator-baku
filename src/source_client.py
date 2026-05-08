import os
import time
from typing import Any

import requests

from .utils import detect_challenge, env_int, join_url, origin


class SourceBlockedError(RuntimeError):
    pass


class SourceClient:
    def __init__(self) -> None:
        self.start_url = os.environ["SOURCE_START_URL"].strip()
        self.base_url = origin(self.start_url)
        self.graphql_url = join_url(self.base_url, os.getenv("SOURCE_GRAPHQL_PATH") or "/graphql")
        self.timeout = env_int("REQUEST_TIMEOUT_SECONDS", 20)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "personal-rent-monitor/1.0",
                "Accept": "application/json,text/html;q=0.8,*/*;q=0.5",
            }
        )

    def get_start_page(self) -> str:
        response = self._request("GET", self.start_url)
        return response.text

    def graphql(self, query: str, variables: dict[str, Any]) -> dict[str, Any]:
        response = self._request(
            "POST",
            self.graphql_url,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        if data.get("errors"):
            raise RuntimeError(str(data["errors"][:2]))
        return data["data"]

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                text = response.text or ""
                if detect_challenge(text, response.status_code):
                    raise SourceBlockedError(f"source blocked or challenged: HTTP {response.status_code}")
                if response.status_code >= 500 and attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                response.raise_for_status()
                return response
            except SourceBlockedError:
                raise
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(1 + attempt)
                    continue
                raise
        raise RuntimeError(str(last_error))
