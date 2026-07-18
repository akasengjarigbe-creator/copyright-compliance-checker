import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.schemas import (
    AttributionEvidence,
    ImageRecord,
    ParsedHtml,
)


LICENCE_PATTERNS = [
    r"CC\s*BY(?:-NC-SA|-NC-ND|-SA|-NC|-ND)?\s*\d\.\d",
    r"Creative Commons",
    r"public domain",
    r"all rights reserved",
]


AUTHOR_PATTERNS = [
    (
        r"photo by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"image by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"author[:\s]+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"creator[:\s]+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
]


def _first_match(
    patterns: list[str],
    text: str
) -> str | None:
    """
    Return the first value matching any supplied pattern.
    """

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            if match.groups():
                return match.group(1).strip()

            return match.group(0).strip()

    return None


def _find_matching_img_tag(
    soup: BeautifulSoup,
    image: ImageRecord,
    base_url: str | None
) -> Tag | None:
    """
    Find the HTML img element that corresponds to an ImageRecord.

    The image detector may convert a relative source such as
    'cat.jpg' into an absolute URL. The original HTML still contains
    the relative source, so each HTML source is resolved before it is
    compared with the ImageRecord source.
    """

    for img_tag in soup.find_all("img"):
        raw_src = img_tag.get("src")

        if not raw_src or not raw_src.strip():
            continue

        raw_src = raw_src.strip()

        resolved_src = (
            urljoin(base_url, raw_src)
            if base_url
            else raw_src
        )

        if resolved_src == image.src:
            return img_tag

    return None


def extract_attribution_evidence(
    parsed: ParsedHtml,
    images: list[ImageRecord]
) -> list[AttributionEvidence]:
    """
    Extract attribution and licence evidence for every detected image.
    """

    soup = BeautifulSoup(parsed.html, "lxml")
    results: list[AttributionEvidence] = []

    for image in images:
        img_tag = _find_matching_img_tag(
            soup,
            image,
            parsed.base_url
        )

        nearby_text = ""
        caption = None
        licence_url = None

        if img_tag:
            parent = img_tag.find_parent()

            if parent:
                nearby_text = parent.get_text(
                    " ",
                    strip=True
                )

            figure = img_tag.find_parent("figure")

            if figure:
                figcaption = figure.find("figcaption")

                if figcaption:
                    caption = figcaption.get_text(
                        " ",
                        strip=True
                    )

            surrounding_tags = img_tag.find_all_next(
                [
                    "p",
                    "figcaption",
                    "footer",
                    "small",
                    "a",
                ],
                limit=5,
            )

            surrounding_text = [
                tag.get_text(" ", strip=True)
                for tag in surrounding_tags
            ]

            nearby_text = " ".join(
                [nearby_text] + surrounding_text
            ).strip()

            for link in img_tag.find_all_next(
                "a",
                limit=10
            ):
                href = link.get("href", "")

                if not href:
                    continue

                href_lower = href.lower()

                if (
                    "creativecommons.org/licenses"
                    in href_lower
                    or "license" in href_lower
                    or "licence" in href_lower
                ):
                    licence_url = (
                        urljoin(parsed.base_url, href)
                        if parsed.base_url
                        else href
                    )
                    break

        combined_text = " ".join(
            filter(
                None,
                [
                    image.alt,
                    image.title,
                    caption,
                    nearby_text,
                ],
            )
        )

        results.append(
            AttributionEvidence(
                image=image,
                nearby_text=nearby_text,
                caption=caption,
                licence_name=_first_match(
                    LICENCE_PATTERNS,
                    combined_text,
                ),
                licence_url=licence_url,
                possible_author=_first_match(
                    AUTHOR_PATTERNS,
                    combined_text,
                ),
            )
        )

    return results