from app.fetcher import CreatorPageFetcher, build_render_data_html


class FakeResponse:
    def __init__(self, *, text: str, content_type: str = 'text/html', status_code: int = 200):
        self.text = text
        self.status_code = status_code
        self.headers = {'content-type': content_type}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f'http {self.status_code}')


class FakeClient:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error

    def get(self, profile_url: str):
        if self.error:
            raise self.error
        return self.response


class FakeBrowserFetcher:
    def __init__(self, html: str):
        self.html = html
        self.called = []

    def fetch(self, profile_url: str) -> str:
        self.called.append(profile_url)
        return self.html


def test_build_render_data_html_wraps_payload():
    html = build_render_data_html({'aweme_list': [{'aweme_id': '1'}]})

    assert 'RENDER_DATA' in html
    assert 'aweme_list' in html
    assert 'aweme_id' in html


def test_creator_page_fetcher_returns_http_html_when_present():
    fetcher = CreatorPageFetcher(
        timeout_seconds=15,
        client=FakeClient(response=FakeResponse(text='<html><script id="RENDER_DATA">{}</script></html>')),
    )

    html = fetcher.fetch('https://example.com/user')

    assert 'RENDER_DATA' in html


def test_creator_page_fetcher_falls_back_to_browser_on_empty_body():
    browser = FakeBrowserFetcher('<html><script id="RENDER_DATA">{}</script></html>')
    fetcher = CreatorPageFetcher(
        timeout_seconds=15,
        client=FakeClient(response=FakeResponse(text='', content_type='application/json')),
        browser_fetcher=browser,
    )

    html = fetcher.fetch('https://example.com/user')

    assert 'RENDER_DATA' in html
    assert browser.called == ['https://example.com/user']


def test_creator_page_fetcher_falls_back_to_browser_on_challenge_shell():
    challenge_html = '<html><head><meta charset="UTF-8" /></head><body></body><script>var __ac_nonce="x";var acrawler={};</script></html>'
    browser = FakeBrowserFetcher('<html><script id="RENDER_DATA">{}</script></html>')
    fetcher = CreatorPageFetcher(
        timeout_seconds=15,
        client=FakeClient(response=FakeResponse(text=challenge_html, content_type='text/html')),
        browser_fetcher=browser,
    )

    html = fetcher.fetch('https://example.com/user')

    assert 'RENDER_DATA' in html
    assert browser.called == ['https://example.com/user']


def test_creator_page_fetcher_falls_back_to_browser_on_http_error():
    browser = FakeBrowserFetcher('<html>browser</html>')
    fetcher = CreatorPageFetcher(
        timeout_seconds=15,
        client=FakeClient(error=RuntimeError('boom')),
        browser_fetcher=browser,
    )

    html = fetcher.fetch('https://example.com/user')

    assert html == '<html>browser</html>'
