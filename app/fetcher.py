from __future__ import annotations

import httpx


class CreatorPageFetcher:
    def __init__(self, *, timeout_seconds: int) -> None:
        self.client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
                )
            },
        )

    def fetch(self, profile_url: str) -> str:
        response = self.client.get(profile_url)
        response.raise_for_status()
        return response.text
