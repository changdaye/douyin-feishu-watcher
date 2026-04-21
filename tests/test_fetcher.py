import pytest

from app.fetcher import CreatorPageFetcher, build_aweme_post_api_url, build_render_data_html


class FakeResponse:
    def __init__(self, *, text: str = '', json_data=None, content_type: str = 'text/html', status_code: int = 200):
        self.text = text
        self._json_data = json_data
        self.status_code = status_code
        self.headers = {'content-type': content_type}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f'http {self.status_code}')

    def json(self):
        if self._json_data is None:
            raise ValueError('no json')
        return self._json_data


class FakeClient:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None, responses_by_url: dict | None = None):
        self.response = response
        self.error = error
        self.responses_by_url = responses_by_url or {}
        self.called_urls = []

    def get(self, profile_url: str):
        self.called_urls.append(profile_url)
        if self.error:
            raise self.error
        if profile_url in self.responses_by_url:
            return self.responses_by_url[profile_url]
        return self.response


def test_build_render_data_html_wraps_payload():
    html = build_render_data_html({'aweme_list': [{'aweme_id': '1'}]})

    assert 'RENDER_DATA' in html
    assert 'aweme_list' in html
    assert 'aweme_id' in html


def test_build_aweme_post_api_url_extracts_sec_user_id():
    url = 'https://www.douyin.com/user/MS4wLjABAAAAnKeRN8QUgooS1pPRqOf_N_jnuztzUyocl0_vUndQFJs?from_tab_name=main&vid=7630812460270247593'

    api_url = build_aweme_post_api_url(url)

    assert 'aweme/v1/web/aweme/post/' in api_url
    assert 'sec_user_id=MS4wLjABAAAAnKeRN8QUgooS1pPRqOf_N_jnuztzUyocl0_vUndQFJs' in api_url
    assert 'count=18' in api_url


def test_creator_page_fetcher_prefers_aweme_api_when_cookie_exists():
    profile_url = 'https://www.douyin.com/user/abc123?from_tab_name=main'
    api_url = build_aweme_post_api_url(profile_url)
    client = FakeClient(
        responses_by_url={
            api_url: FakeResponse(
                json_data={
                    'aweme_list': [
                        {'aweme_id': '1', 'desc': 'hello', 'share_url': 'https://www.douyin.com/video/1'}
                    ]
                },
                content_type='application/json',
            )
        }
    )
    fetcher = CreatorPageFetcher(timeout_seconds=15, client=client, douyin_cookie='sessionid=test')

    html = fetcher.fetch(profile_url)

    assert client.called_urls == [api_url]
    assert 'RENDER_DATA' in html
    assert 'aweme_list' in html
    assert 'hello' in html


def test_creator_page_fetcher_returns_http_html_when_present():
    fetcher = CreatorPageFetcher(
        timeout_seconds=15,
        client=FakeClient(response=FakeResponse(text='<html><script id="RENDER_DATA">{}</script></html>')),
    )

    html = fetcher.fetch('https://example.com/user')

    assert 'RENDER_DATA' in html


def test_creator_page_fetcher_raises_when_douyin_html_is_challenge_shell_without_cookie():
    challenge_html = '<html><head><meta charset="UTF-8" /></head><body></body><script>var __ac_nonce="x";var acrawler={};</script></html>'
    fetcher = CreatorPageFetcher(
        timeout_seconds=15,
        client=FakeClient(response=FakeResponse(text=challenge_html, content_type='text/html')),
    )

    with pytest.raises(RuntimeError, match='DOUYIN_COOKIE'):
        fetcher.fetch('https://www.douyin.com/user/abc123')


def test_creator_page_fetcher_raises_on_http_error_without_cookie():
    fetcher = CreatorPageFetcher(
        timeout_seconds=15,
        client=FakeClient(error=RuntimeError('boom')),
    )

    with pytest.raises(RuntimeError, match='boom'):
        fetcher.fetch('https://example.com/user')
