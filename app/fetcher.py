from __future__ import annotations

import json
from contextlib import suppress
from urllib.parse import urlparse

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


def extract_sec_user_id(profile_url: str) -> str | None:
    parsed = urlparse(profile_url)
    parts = [part for part in parsed.path.split('/') if part]
    if len(parts) >= 2 and parts[0] == 'user':
        return parts[1]
    return None


def build_aweme_post_api_url(profile_url: str) -> str:
    sec_user_id = extract_sec_user_id(profile_url)
    if not sec_user_id:
        raise ValueError(f'Unsupported Douyin profile URL: {profile_url}')
    return (
        'https://www.douyin.com/aweme/v1/web/aweme/post/'
        '?device_platform=webapp&aid=6383&channel=channel_pc_web'
        f'&sec_user_id={sec_user_id}'
        '&max_cursor=0&locate_query=false&show_live_replay_strategy=1'
        '&need_time_list=1&time_list_query=0&whale_cut_token=&cut_version=1'
        '&count=18&publish_video_strategy_type=2&from_user_page=1'
        '&version_code=290100&version_name=29.1.0'
    )


class PlaywrightBrowserFetcher:
    def __init__(self, *, timeout_seconds: int, user_agent: str = DEFAULT_USER_AGENT, douyin_cookie: str | None = None) -> None:
        from playwright.sync_api import sync_playwright

        self.timeout_ms = timeout_seconds * 1000
        self.user_agent = user_agent
        self.douyin_cookie = douyin_cookie
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
        if self.douyin_cookie:
            cookies = []
            for part in self.douyin_cookie.split(';'):
                item = part.strip()
                if not item or '=' not in item:
                    continue
                name, value = item.split('=', 1)
                name = name.strip()
                value = value.strip()
                if name and value:
                    cookies.append({'name': name, 'value': value, 'domain': '.douyin.com', 'path': '/'})
            if cookies:
                self._context.add_cookies(cookies)
        return self._context

    def fetch(self, profile_url: str) -> str:
        context = self._ensure_context()
        page = context.new_page()
        try:
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
    def __init__(self, *, timeout_seconds: int, client=None, browser_fetcher=None, douyin_cookie: str | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        self.douyin_cookie = douyin_cookie
        headers = {
            'User-Agent': DEFAULT_USER_AGENT,
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.douyin.com/',
        }
        if douyin_cookie:
            headers['Cookie'] = douyin_cookie
        self.client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            verify=False,
            headers=headers,
        )
        self.browser_fetcher = browser_fetcher or PlaywrightBrowserFetcher(
            timeout_seconds=timeout_seconds,
            douyin_cookie=douyin_cookie,
        )

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

    def _fetch_via_aweme_api(self, profile_url: str) -> str | None:
        if not self.douyin_cookie:
            return None
        sec_user_id = extract_sec_user_id(profile_url)
        if not sec_user_id:
            return None
        api_url = build_aweme_post_api_url(profile_url)
        response = self.client.get(api_url)
        response.raise_for_status()
        data = response.json()
        aweme_list = data.get('aweme_list') if isinstance(data, dict) else None
        if aweme_list:
            return build_render_data_html({'aweme_list': aweme_list})
        return None

    def fetch(self, profile_url: str) -> str:
        try:
            api_html = self._fetch_via_aweme_api(profile_url)
            if api_html:
                return api_html
        except Exception:
            pass

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
