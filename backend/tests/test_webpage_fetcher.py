import pytest
import requests

from app.crawler.webpage_fetcher import (
    WebpageFetchError,
    fetch_webpage_html,
    validate_webpage_url,
)


class FakeResponse:
    """
    A small fake response object used to test the crawler
    without accessing the real internet.
    """

    def __init__(
        self,
        text: str,
        content_type: str = "text/html",
        status_error: Exception | None = None,
    ):
        self.text = text
        self.headers = {
            "Content-Type": content_type
        }
        self.status_error = status_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error


def test_validate_webpage_url_accepts_https():
    validate_webpage_url(
        "https://example.com/coursework/page.html"
    )


def test_validate_webpage_url_rejects_file_scheme():
    with pytest.raises(
        WebpageFetchError,
        match="Only HTTP and HTTPS"
    ):
        validate_webpage_url(
            "file:///C:/private-file.html"
        )


def test_fetch_webpage_html_returns_html(monkeypatch):
    fake_html = """
    <html>
        <body>
            <h1>Student coursework</h1>
        </body>
    </html>
    """

    def fake_get(*args, **kwargs):
        return FakeResponse(
            text=fake_html,
            content_type="text/html"
        )

    monkeypatch.setattr(
        requests,
        "get",
        fake_get
    )

    result = fetch_webpage_html(
        "https://example.com/coursework/page.html"
    )

    assert "Student coursework" in result


def test_fetch_webpage_html_rejects_non_html_content(
    monkeypatch
):
    def fake_get(*args, **kwargs):
        return FakeResponse(
            text="PDF file contents",
            content_type="application/pdf"
        )

    monkeypatch.setattr(
        requests,
        "get",
        fake_get
    )

    with pytest.raises(
        WebpageFetchError,
        match="did not return an HTML webpage"
    ):
        fetch_webpage_html(
            "https://example.com/document.pdf"
        )