from urllib.parse import urlparse

import requests


class WebpageFetchError(Exception):
    """
    Raised when a webpage cannot be safely or successfully retrieved.
    """


def validate_webpage_url(url: str) -> None:
    """
    Validate that the supplied URL uses HTTP or HTTPS.

    Args:
        url:
            The webpage address supplied by the user.

    Raises:
        WebpageFetchError:
            If the URL is empty or uses an unsupported scheme.
    """

    if not url or not url.strip():
        raise WebpageFetchError(
            "A webpage URL must be provided."
        )

    parsed_url = urlparse(url.strip())

    if parsed_url.scheme not in {"http", "https"}:
        raise WebpageFetchError(
            "Only HTTP and HTTPS webpage URLs are supported."
        )

    if not parsed_url.netloc:
        raise WebpageFetchError(
            "The supplied webpage URL does not contain a valid host."
        )


def fetch_webpage_html(
    url: str,
    timeout_seconds: int = 10
) -> str:
    """
    Download HTML content from a webpage.

    Args:
        url:
            The webpage address to retrieve.

        timeout_seconds:
            Maximum time to wait for the server to respond.

    Returns:
        The downloaded HTML as text.

    Raises:
        WebpageFetchError:
            If the URL is invalid, the request fails, or the response
            does not contain HTML.
    """

    validate_webpage_url(url)

    try:
        response = requests.get(
            url.strip(),
            timeout=timeout_seconds,
            headers={
                "User-Agent": (
                    "Copyright-Compliance-Checker/0.1 "
                    "(Academic Research Project)"
                )
            },
        )

        response.raise_for_status()

    except requests.RequestException as error:
        raise WebpageFetchError(
            f"The webpage could not be retrieved: {error}"
        ) from error

    content_type = response.headers.get(
        "Content-Type",
        ""
    ).lower()

    if (
        "text/html" not in content_type
        and "application/xhtml+xml" not in content_type
    ):
        raise WebpageFetchError(
            "The supplied URL did not return an HTML webpage."
        )

    if not response.text.strip():
        raise WebpageFetchError(
            "The retrieved webpage contained no HTML content."
        )

    return response.text