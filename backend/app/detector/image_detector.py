from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.schemas import ImageRecord, ParsedHtml


TRACKING_SOURCE_TERMS = [
    "tracking-pixel",
    "tracking_pixel",
    "tracking.gif",
    "pixel.gif",
    "spacer.gif",
    "transparent.gif",
    "web-beacon",
    "web_beacon",
    "beacon.gif",
]


def _parse_dimension(value: object) -> int | None:
    """
    Convert an HTML width or height value into an integer.

    Examples:
        "1" -> 1
        "20px" -> 20
        None -> None
    """

    if value is None:
        return None

    text = str(value).strip().lower()

    if text.endswith("px"):
        text = text[:-2].strip()

    try:
        return int(float(text))
    except ValueError:
        return None


def _is_hidden_image(img: Tag) -> bool:
    """
    Check whether the image is explicitly hidden in the HTML.
    """

    hidden_attribute = img.has_attr("hidden")

    aria_hidden = (
        str(img.get("aria-hidden", "")).strip().lower()
        == "true"
    )

    style = str(img.get("style", "")).replace(" ", "").lower()

    hidden_style = (
        "display:none" in style
        or "visibility:hidden" in style
    )

    return hidden_attribute or aria_hidden or hidden_style


def _is_tiny_tracking_image(img: Tag) -> bool:
    """
    Detect images that are explicitly declared as 1x1 or 2x2 pixels.

    These are commonly used as tracking pixels rather than visible
    webpage content.
    """

    width = _parse_dimension(img.get("width"))
    height = _parse_dimension(img.get("height"))

    if width is None or height is None:
        return False

    return width <= 2 and height <= 2


def _has_tracking_source(src: str) -> bool:
    """
    Detect clear tracking or spacer image filenames.
    """

    source_lower = src.lower()

    return any(
        term in source_lower
        for term in TRACKING_SOURCE_TERMS
    )


def _should_ignore_image(
    img: Tag,
    src: str,
) -> bool:
    """
    Decide whether an image is clearly a technical, hidden,
    or tracking asset.

    This filter is deliberately conservative so that normal content
    images, logos, diagrams, and icons are not removed automatically.
    """

    return (
        _is_hidden_image(img)
        or _is_tiny_tracking_image(img)
        or _has_tracking_source(src)
    )


def detect_images(
    parsed: ParsedHtml,
) -> list[ImageRecord]:
    """
    Detect valid content image elements in parsed HTML.
    """

    soup = BeautifulSoup(parsed.html, "lxml")
    images: list[ImageRecord] = []

    for img in soup.find_all("img"):
        src = img.get("src")

        if not src or not src.strip():
            continue

        src = src.strip()

        if _should_ignore_image(img, src):
            continue

        if parsed.base_url:
            src = urljoin(parsed.base_url, src)

        images.append(
            ImageRecord(
                src=src,
                alt=img.get("alt"),
                title=img.get("title"),
            )
        )

    return images