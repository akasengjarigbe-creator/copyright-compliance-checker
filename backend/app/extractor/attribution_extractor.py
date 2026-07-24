import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.schemas import (
    AttributionEvidence,
    ImageRecord,
    ParsedHtml,
)


SELF_AUTHORED_LICENCE = "Self-authored claim"


LICENCE_PATTERNS = [
    r"\bCC\s*BY(?:-NC-SA|-NC-ND|-SA|-NC|-ND)?\s*\d(?:\.\d)?\b",
    r"\bCreative Commons(?:\s+[A-Za-z0-9.\-]+)?\b",
    r"\bPexels\s+(?:License|Licence)\b",
    r"\bUnsplash\s+(?:License|Licence)\b",
    r"\bPixabay(?:\s+Content)?\s+(?:License|Licence)\b",
    r"\bpublic domain\b",
    r"\ball rights reserved\b",
]


AUTHOR_PATTERNS = [
    (
        r"\bphoto by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bphotograph by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bimage by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bcreated by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\btaken by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bphotographer[:\s]+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bauthor[:\s]+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bcreator[:\s]+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bimage\s*:\s*[\"“][^\"”]+[\"”]\s*(?:by\s+)?(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under\s+CC|CC\s+BY)"
        r"|[.;,\n]|$)"
    ),
    (
        r"©\s*(?:\d{4}\s*)?(.+?)"
        r"(?=[.;,\n]|$)"
    ),
]


SELF_AUTHORSHIP_PATTERNS = [
    r"\bself[-\s]?authored\b",
    r"\bself[-\s]?created\b",
    r"\bself[-\s]?produced\b",
    r"\bmy own (?:image|photo|photograph|picture|work)\b",
    r"\b(?:this|the) (?:image|photo|photograph|picture) is my own\b",
    (
        r"\b(?:image|photo|photograph|picture) "
        r"(?:created|taken|made|produced|photographed) by me\b"
    ),
    (
        r"\bI (?:created|took|made|produced|photographed) "
        r"(?:this|the) (?:image|photo|photograph|picture)\b"
    ),
    r"\bowned by me\b",
    r"\bcopyright belongs to me\b",
]


LICENCE_URL_MARKERS = [
    "creativecommons.org/licenses",
    "creativecommons.org/publicdomain",
    "pexels.com/license",
    "unsplash.com/license",
    "pixabay.com/service/license",
    "pixabay.com/service/terms",
]


def _normalise_whitespace(
    value: str,
) -> str:
    """
    Collapse repeated whitespace and trim surrounding spaces.
    """

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _clean_author_name(
    value: str | None,
) -> str | None:
    """
    Clean punctuation and common trailing attribution words
    from an extracted author name.
    """

    if not value:
        return None

    cleaned = _normalise_whitespace(
        value
    )

    cleaned = re.sub(
        r"\s+(?:licensed?|licenced?|copyright|under)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = cleaned.strip(
        " \t\r\n,.;:()[]{}\"'“”"
    )

    if not cleaned:
        return None

    return cleaned


def _first_match(
    patterns: list[str],
    text: str,
) -> str | None:
    """
    Return the first value matching any supplied pattern.
    """

    if not text:
        return None

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        if match.groups():
            value = match.group(1)
        else:
            value = match.group(0)

        return _normalise_whitespace(
            value
        )

    return None


def _contains_self_authorship_claim(
    text: str,
) -> bool:
    """
    Detect an explicit first-person ownership statement.
    """

    if not text:
        return False

    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern in SELF_AUTHORSHIP_PATTERNS
    )


def _extract_page_identity(
    soup: BeautifulSoup,
) -> str | None:
    """
    Extract a likely page-author identity.

    Explicit metadata is preferred. Portrait alt text is used
    only as a fallback.
    """

    meta_author = soup.find(
        "meta",
        attrs={
            "name": re.compile(
                r"^author$",
                re.IGNORECASE,
            )
        },
    )

    if meta_author:
        content = meta_author.get(
            "content"
        )

        if isinstance(content, str):
            content = _normalise_whitespace(
                content
            )

            if content:
                return content

    author_rel = soup.find(
        attrs={
            "rel": re.compile(
                r"\bauthor\b",
                re.IGNORECASE,
            )
        }
    )

    if isinstance(author_rel, Tag):
        author_text = author_rel.get_text(
            " ",
            strip=True,
        )

        if author_text:
            return _normalise_whitespace(
                author_text
            )

    for img_tag in soup.find_all(
        "img"
    ):
        alt = img_tag.get(
            "alt",
            "",
        )

        if not isinstance(alt, str):
            continue

        match = re.match(
            r"\s*portrait of\s+(.+?)\s*$",
            alt,
            flags=re.IGNORECASE,
        )

        if match:
            return _normalise_whitespace(
                match.group(1)
            )

    return None


def _same_person(
    first: str | None,
    second: str | None,
) -> bool:
    """
    Compare two names conservatively after normalisation.
    """

    if not first or not second:
        return False

    def normalise_name(
        value: str,
    ) -> str:
        value = value.casefold()
        value = re.sub(
            r"[^\w\s-]",
            "",
            value,
        )
        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    return (
        normalise_name(first)
        == normalise_name(second)
    )


def _find_matching_img_tag(
    soup: BeautifulSoup,
    image: ImageRecord,
    base_url: str | None,
) -> Tag | None:
    """
    Find the HTML img element corresponding to an ImageRecord.
    """

    for img_tag in soup.find_all(
        "img"
    ):
        raw_src = img_tag.get(
            "src"
        )

        if not isinstance(
            raw_src,
            str,
        ):
            continue

        raw_src = raw_src.strip()

        if not raw_src:
            continue

        resolved_src = (
            urljoin(
                base_url,
                raw_src,
            )
            if base_url
            else raw_src
        )

        if resolved_src == image.src:
            return img_tag

        if raw_src == image.src:
            return img_tag

    return None


def _is_small_local_container(
    container: Tag,
) -> bool:
    """
    Return True when a parent is local to one image rather
    than a large page-level container.
    """

    if container.name in {
        "html",
        "body",
        "main",
    }:
        return False

    images = container.find_all(
        "img"
    )

    return len(images) <= 1


def _collect_local_tags(
    img_tag: Tag,
) -> list[Tag]:
    """
    Collect a bounded set of tags associated with one image.

    Collection stops before another image or figure so that
    attribution evidence does not leak between images.
    """

    tags: list[Tag] = []

    figure = img_tag.find_parent(
        "figure"
    )

    if isinstance(
        figure,
        Tag,
    ):
        tags.append(
            figure
        )
        anchor: Tag = figure

    else:
        parent = img_tag.parent

        if (
            isinstance(
                parent,
                Tag,
            )
            and _is_small_local_container(
                parent
            )
        ):
            tags.append(
                parent
            )
            anchor = parent
        else:
            anchor = img_tag

    sibling_count = 0

    for sibling in anchor.next_siblings:
        if not isinstance(
            sibling,
            Tag,
        ):
            continue

        if sibling.name == "figure":
            break

        if (
            sibling.name == "img"
            or sibling.find(
                "img"
            )
        ):
            break

        if sibling.name in {
            "p",
            "small",
            "footer",
            "figcaption",
            "a",
            "div",
            "span",
        }:
            tags.append(
                sibling
            )
            sibling_count += 1

        if sibling_count >= 4:
            break

    unique_tags: list[Tag] = []
    seen_ids: set[int] = set()

    for tag in tags:
        tag_id = id(
            tag
        )

        if tag_id in seen_ids:
            continue

        seen_ids.add(
            tag_id
        )
        unique_tags.append(
            tag
        )

    return unique_tags


def _extract_caption(
    img_tag: Tag,
) -> str | None:
    """
    Extract a figure caption associated with an image.
    """

    figure = img_tag.find_parent(
        "figure"
    )

    if not isinstance(
        figure,
        Tag,
    ):
        return None

    figcaption = figure.find(
        "figcaption"
    )

    if not isinstance(
        figcaption,
        Tag,
    ):
        return None

    text = figcaption.get_text(
        " ",
        strip=True,
    )

    if not text:
        return None

    return _normalise_whitespace(
        text
    )


def _extract_nearby_text(
    tags: list[Tag],
) -> str:
    """
    Combine visible text from the bounded local image context.
    """

    text_parts: list[str] = []

    for tag in tags:
        text = tag.get_text(
            " ",
            strip=True,
        )

        if not text:
            continue

        normalised = _normalise_whitespace(
            text
        )

        if (
            normalised
            and normalised not in text_parts
        ):
            text_parts.append(
                normalised
            )

    return " ".join(
        text_parts
    ).strip()


def _extract_licence_url(
    tags: list[Tag],
    base_url: str | None,
) -> str | None:
    """
    Extract a recognised licence URL from the current
    image's bounded attribution context.
    """

    for tag in tags:
        if tag.name == "a":
            links = [
                tag
            ]
        else:
            links = list(
                tag.find_all(
                    "a"
                )
            )

        for link in links:
            href = link.get(
                "href",
                "",
            )

            if not isinstance(
                href,
                str,
            ):
                continue

            href = href.strip()

            if not href:
                continue

            href_lower = href.casefold()

            if not any(
                marker in href_lower
                for marker in LICENCE_URL_MARKERS
            ):
                continue

            return (
                urljoin(
                    base_url,
                    href,
                )
                if base_url
                else href
            )

    return None


def _build_combined_text(
    image: ImageRecord,
    caption: str | None,
    nearby_text: str,
) -> str:
    """
    Combine all relevant textual evidence for one image.
    """

    values = [
        image.alt,
        image.title,
        caption,
        nearby_text,
    ]

    parts = [
        _normalise_whitespace(
            value
        )
        for value in values
        if isinstance(
            value,
            str,
        )
        and value.strip()
    ]

    return " ".join(
        parts
    )


def extract_attribution_evidence(
    parsed: ParsedHtml,
    images: list[ImageRecord],
) -> list[AttributionEvidence]:
    """
    Extract bounded attribution and licence evidence for
    every detected image.
    """

    soup = BeautifulSoup(
        parsed.html,
        "lxml",
    )

    page_identity = _extract_page_identity(
        soup
    )

    results: list[
        AttributionEvidence
    ] = []

    for image in images:
        img_tag = _find_matching_img_tag(
            soup,
            image,
            parsed.base_url,
        )

        caption: str | None = None
        nearby_text = ""
        licence_url: str | None = None

        if img_tag is not None:
            local_tags = _collect_local_tags(
                img_tag
            )

            caption = _extract_caption(
                img_tag
            )

            nearby_text = _extract_nearby_text(
                local_tags
            )

            licence_url = _extract_licence_url(
                local_tags,
                parsed.base_url,
            )

        combined_text = _build_combined_text(
            image,
            caption,
            nearby_text,
        )

        possible_author = _clean_author_name(
            _first_match(
                AUTHOR_PATTERNS,
                combined_text,
            )
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

        named_page_author_claim = (
            _same_person(
                possible_author,
                page_identity,
            )
        )

        if (
            explicit_self_claim
            and not possible_author
        ):
            possible_author = (
                page_identity
            )

        if (
            not licence_name
            and (
                explicit_self_claim
                or named_page_author_claim
            )
        ):
            licence_name = (
                SELF_AUTHORED_LICENCE
            )

        if (
            licence_name
            and licence_name.casefold()
            == SELF_AUTHORED_LICENCE.casefold()
        ):
            licence_url = None

        results.append(
            AttributionEvidence(
                image=image,
                nearby_text=nearby_text,
                caption=caption,
                possible_author=possible_author,
                licence_name=licence_name,
                licence_url=licence_url,
            )
        )

    return results