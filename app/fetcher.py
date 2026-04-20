from __future__ import annotations

import json
from contextlib import suppress

import httpx


DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
)


def build_render_data_html(payload: dict) -> str:
    return (
        '<html><body>'
        f'<script id="RENDER_DATA" type="application/json">{json.dumps(payload, ensure_ascii=False)}</script>'
        '</body></html>'
    )


class PlaywrightBrowserFetcher:
    def __init__(self, *, timeout_seconds: int, user_agent: str = DEFAULT_USER_AGENT) -> None:
        from playwright.sync_api import sync_playwright

        self.timeout_ms = timeout_seconds * 1000
        self.user_agent = user_agent
        self._sync_playwright = sync_playwright
        self._playwright = None
        self._browser = None
        self._context = None

    def _ensure_context(self):
        if self._context is not None:
            return self._context

        self._playwright = self._sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        self._context = self._browser.new_context(locale='zh-CN', user_agent=self.user_agent)
        return self._context

    def fetch(self, profile_url: str) -> str:
        context = self._ensure_context()
        page = context.new_page()
        try:
            try:
                with page.expect_response(lambda response: '/aweme/v1/web/aweme/post/' in response.url and response.status == 200, timeout=self.timeout_ms) as response_info:
                    page.goto(profile_url, wait_until='domcontentloaded', timeout=self.timeout_ms)
                data = response_info.value.json()
                aweme_list = data.get('aweme_list') if isinstance(data, dict) else None
                if aweme_list:
                    return build_render_data_html({'aweme_list': aweme_list})
            except Exception:
                page.goto(profile_url, wait_until='domcontentloaded', timeout=self.timeout_ms)

            page.wait_for_timeout(8000)
            return page.content()
        finally:
            page.close()

    def close(self) -> None:
        with suppress(Exception):
            if self._context is not None:
                self._context.close()
        with suppress(Exception):
            if self._browser is not None:
                self._browser.close()
        with suppress(Exception):
            if self._playwright is not None:
                self._playwright.stop()
        self._context = None
        self._browser = None
        self._playwright = None


class CreatorPageFetcher:
    def __init__(self, *, timeout_seconds: int, client=None, browser_fetcher=None) -> None:
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                'User-Agent': DEFAULT_USER_AGENT,
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.douyin.com/',
            },
        )
        self.browser_fetcher = browser_fetcher or PlaywrightBrowserFetcher(timeout_seconds=timeout_seconds)

    def _response_needs_browser_fallback(self, response: httpx.Response | object) -> bool:
        text = getattr(response, 'text', '') or ''
        headers = getattr(response, 'headers', {}) or {}
        content_type = str(headers.get('content-type', '')).lower()
        lowered = text.lower()

        if not text.strip():
            return True
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            return True
        if '__ac_nonce' in lowered or 'acrawler' in lowered:
            return True
        if 'script id="render_data"' not in lowered and "script id='render_data'" not in lowered:
            return True
        return False

    def fetch(self, profile_url: str) -> str:
        try:
            response = self.client.get(profile_url)
            response.raise_for_status()
            if self._response_needs_browser_fallback(response):
                return self.browser_fetcher.fetch(profile_url)
            return response.text
        except Exception:
            return self.browser_fetcher.fetch(profile_url)

    def close(self) -> None:
        close_fn = getattr(self.browser_fetcher, 'close', None)
        if callable(close_fn):
            close_fn()
