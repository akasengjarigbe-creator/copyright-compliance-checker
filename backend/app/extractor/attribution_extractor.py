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
    r"Creative Commons(?:\s+[A-Za-z0-9.\-]+)?",
    r"Pexels\s+(?:License|Licence)",
    r"Unsplash\s+(?:License|Licence)",
    r"Pixabay(?:\s+Content)?\s+(?:License|Licence)",
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
        r"image\s*:\s*[\"“][^\"”]+[\"”]\s*(?:by\s+)?(.+?)"
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
    (
        r"©\s*(?:\d{4}\s*)?(.+?)"
        r"(?=[.;,\n]|$)"
    ),
]


SELF_AUTHORSHIP_PATTERNS = [
    r"\bmy own (?:image|photo|photograph|work)\b",
    r"\b(?:image|photo|photograph) (?:created|taken|made) by me\b",
    r"\bI (?:created|took|made|photographed) (?:this|the) "
    r"(?:image|photo|photograph)\b",
]


LICENCE_URL_MARKERS = [
    "creativecommons.org/licenses",
    "pexels.com/license",
    "unsplash.com/license",
    "pixabay.com/service/license",
    "pixabay.com/service/terms",
]


def _first_match(
    patterns: list[str],
    text: str,
) -> str | None:
    """
    Return the first value matching any supplied pattern.
    """

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        if match.groups():
            return match.group(1).strip()

        return match.group(0).strip()

    return None


def _contains_self_authorship_claim(
    text: str,
) -> bool:
    """
    Detect explicit first-person ownership statements.
    """

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in SELF_AUTHORSHIP_PATTERNS
    )


def _extract_page_identity(
    soup: BeautifulSoup,
) -> str | None:
    """
    Extract a likely page-author identity.

    This uses explicit author metadata first, then a portrait
    description such as 'Portrait of Student B'.
    """

    meta_author = soup.find(
        "meta",
        attrs={"name": re.compile("^author$", re.IGNORECASE)},
    )

    if meta_author:
        content = meta_author.get("content")

        if content and content.strip():
            return content.strip()

    for img_tag in soup.find_all("img"):
        alt = img_tag.get("alt", "")

        match = re.match(
            r"\s*portrait of\s+(.+?)\s*$",
            alt,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

    return None


def _same_person(
    first: str | None,
    second: str | None,
) -> bool:
    """
    Compare two extracted names conservatively.
    """

    if not first or not second:
        return False

    normalise = lambda value: re.sub(
        r"\s+",
        " ",
        value.strip().casefold(),
    )

    return normalise(first) == normalise(second)


def _find_matching_img_tag(
    soup: BeautifulSoup,
    image: ImageRecord,
    base_url: str | None,
) -> Tag | None:
    """
    Find the HTML img element corresponding to an ImageRecord.
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


def _is_small_local_container(
    container: Tag,
) -> bool:
    """
    Return True when a parent is local to one image rather
    than a large page-level container.
    """

    if container.name in {"html", "body"}:
        return False

    images = container.find_all("img")

    return len(images) <= 1


def _collect_local_tags(
    img_tag: Tag,
) -> list[Tag]:
    """
    Collect only tags belonging to the current image.

    Collection stops when the next image or figure begins,
    preventing attribution evidence from leaking between images.
    """

    tags: list[Tag] = []

    figure = img_tag.find_parent("figure")

    if figure:
        tags.append(figure)
        anchor = figure
    else:
        parent = img_tag.find_parent()

        if parent and _is_small_local_container(parent):
            tags.append(parent)
            anchor = parent
        else:
            anchor = img_tag

    sibling_count = 0

    for sibling in anchor.next_siblings:
        if not isinstance(sibling, Tag):
            continue

        if sibling.name == "figure":
            break

        if sibling.name == "img" or sibling.find("img"):
            break

        if sibling.name in {
            "p",
            "small",
            "footer",
            "figcaption",
            "a",
            "div",
        }:
            tags.append(sibling)
            sibling_count += 1

        if sibling_count >= 4:
            break

    unique_tags: list[Tag] = []
    seen_ids: set[int] = set()

    for tag in tags:
        tag_id = id(tag)

        if tag_id not in seen_ids:
            seen_ids.add(tag_id)
            unique_tags.append(tag)

    return unique_tags


def _extract_licence_url(
    tags: list[Tag],
    base_url: str | None,
) -> str | None:
    """
    Extract a licence URL only from the current image's
    bounded attribution context.
    """

    for tag in tags:
        links: list[Tag]

        if tag.name == "a":
            links = [tag]
        else:
            links = list(tag.find_all("a"))

        for link in links:
            href = link.get("href", "")

            if not href:
                continue

            href_lower = href.casefold()

            if any(
                marker in href_lower
                for marker in LICENCE_URL_MARKERS
            ):
                return (
                    urljoin(base_url, href)
                    if base_url
                    else href
                )

    return None


def extract_attribution_evidence(
    parsed: ParsedHtml,
    images: list[ImageRecord],
) -> list[AttributionEvidence]:
    """
    Extract bounded attribution and licence evidence
    for every detected image.
    """

    soup = BeautifulSoup(
        parsed.html,
        "lxml",
    )

    page_identity = _extract_page_identity(
        soup
    )

    results: list[AttributionEvidence] = []

    for image in images:
        img_tag = _find_matching_img_tag(
            soup,
            image,
            parsed.base_url,
        )

        nearby_text = ""
        caption = None
        licence_url = None

        local_tags: list[Tag] = []

        if img_tag:
            figure = img_tag.find_parent("figure")

            if figure:
                figcaption = figure.find("figcaption")

                if figcaption:
                    caption = figcaption.get_text(
                        " ",
                        strip=True,
                    )

            local_tags = _collect_local_tags(
                img_tag
            )

            local_text_parts = [
                tag.get_text(
                    " ",
                    strip=True,
                )
                for tag in local_tags
            ]

            nearby_text = " ".join(
                part
                for part in local_text_parts
                if part
            ).strip()

            licence_url = _extract_licence_url(
                local_tags,
                parsed.base_url,
            )

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

        possible_author = _first_match(
            AUTHOR_PATTERNS,
            combined_text,
        )

        licence_name = _first_match(
            LICENCE_PATTERNS,
            combined_text,
        )

        explicit_self_claim = (
            _contains_self_authorship_claim(
                combined_text
            )
        )

        named_page_author_claim = _same_person(
            possible_author,
            page_identity,
        )

        if (
            not licence_name
            and (
                explicit_self_claim
                or named_page_author_claim
            )
        ):
            licence_name = "Self-authored claim"

        results.append(
            AttributionEvidence(
                image=image,
                nearby_text=nearby_text,
                caption=caption,
                licence_name=licence_name,
                licence_url=licence_url,
                possible_author=possible_author,
            )
        )

    return results