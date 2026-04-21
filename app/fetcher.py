from __future__ import annotations

import json
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


class CreatorPageFetcher:
    def __init__(self, *, timeout_seconds: int, client=None, douyin_cookie: str | None = None) -> None:
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

    def _response_contains_usable_render_data(self, response: httpx.Response | object) -> bool:
        text = getattr(response, 'text', '') or ''
        headers = getattr(response, 'headers', {}) or {}
        content_type = str(headers.get('content-type', '')).lower()
        lowered = text.lower()

        if not text.strip():
            return False
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            return False
        if '__ac_nonce' in lowered or 'acrawler' in lowered:
            return False
        if 'script id="render_data"' not in lowered and "script id='render_data'" not in lowered:
            return False
        return True

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
        api_error: Exception | None = None
        try:
            api_html = self._fetch_via_aweme_api(profile_url)
            if api_html:
                return api_html
        except Exception as exc:
            api_error = exc

        try:
            response = self.client.get(profile_url)
            response.raise_for_status()
            if self._response_contains_usable_render_data(response):
                return response.text

            sec_user_id = extract_sec_user_id(profile_url)
            if sec_user_id and not self.douyin_cookie:
                raise RuntimeError('Douyin creator pages require DOUYIN_COOKIE for stable HTTP access')
            if sec_user_id:
                raise RuntimeError('Douyin creator page HTML is not usable even after cookie-authenticated API fallback')
            raise RuntimeError(f'HTTP response did not contain usable render data for {profile_url}')
        except Exception as exc:
            if api_error is not None:
                raise RuntimeError(f'Failed to fetch Douyin creator data via API and HTML fallback: {api_error}; {exc}') from exc
            raise

    def close(self) -> None:
        close_fn = getattr(self.client, 'close', None)
        if callable(close_fn):
            close_fn()
