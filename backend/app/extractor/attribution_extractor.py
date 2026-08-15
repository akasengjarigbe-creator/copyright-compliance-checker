import re
from urllib.parse import (
    urljoin,
    urlparse,
)

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.models.schemas import (
    AttributionEvidence,
    ImageRecord,
    ParsedHtml,
)


SELF_AUTHORED_LICENCE = "Self-authored claim"


# ============================================================
# LICENCE PATTERNS
# ============================================================


LICENCE_PATTERNS = [
    (
        r"\bCC\s*BY(?:-NC-SA|-NC-ND|-NC|-ND|-SA)?"
        r"\s*(?:1\.0|2\.0|2\.5|3\.0|4\.0)\b"
    ),
    r"\bCC0(?:\s*1\.0)?\b",
    r"\bCreative Commons(?:\s+[A-Za-z0-9.\-]+){0,6}\b",
    r"\bPexels\s+(?:License|Licence)\b",
    r"\bUnsplash\s+(?:License|Licence)\b",
    r"\bPixabay(?:\s+Content)?\s+(?:License|Licence)\b",
    r"\bMIT\s+License\b",
    r"\bApache\s+License(?:\s+2\.0)?\b",
    r"\bGNU\s+General\s+Public\s+License\b",
    r"\bGPL(?:v?[123])?\b",
    r"\bLGPL(?:v?[123])?\b",
    r"\bBSD\s+(?:2-Clause|3-Clause)?\s*License\b",
    r"\bMozilla\s+Public\s+License\b",
    r"\bOpen\s+Data\s+Commons\b",
    r"\bOpen\s+Government\s+Licence\b",
    r"\bOpen\s+Government\s+License\b",
    r"\bFree\s+Art\s+License\b",
    r"\bFree\s+Art\s+Licence\b",
    r"\bArtistic\s+License\b",
    r"\bArtistic\s+Licence\b",
    r"\bpublic domain\b",
    r"\ball rights reserved\b",
    (
        r"\blicen[cs]ed\s+under\s+"
        r"(.+?)(?=[.;\n]|$)"
    ),
    (
        r"\blicen[cs]e\s*:\s*"
        r"(.+?)(?=[.;\n]|$)"
    ),
]


# ============================================================
# AUTHOR PATTERNS
# ============================================================


AUTHOR_PATTERNS = [
    (
        r"\bphoto by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bphotograph by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bimage by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bcreated by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\btaken by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bphotographed by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under)"
        r"|[.;,\n]|$)"
    ),
    (
        r"\bphotographer\s*[:\-]\s*(.+?)"
        r"(?=[.;,\n]|$)"
    ),
    (
        r"\bauthor\s*[:\-]\s*(.+?)"
        r"(?=[.;,\n]|$)"
    ),
    (
        r"\bcreator\s*[:\-]\s*(.+?)"
        r"(?=[.;,\n]|$)"
    ),
    (
        r"\bcopyright\s+(?:owner|holder)"
        r"\s*[:\-]\s*(.+?)"
        r"(?=[.;,\n]|$)"
    ),
    (
        r"\bcopyright\s*[:\-]\s*(.+?)"
        r"(?=[.;,\n]|$)"
    ),
    (
        r"\bimage\s*:\s*[\"“][^\"”]+[\"”]"
        r"\s+by\s+(.+?)"
        r"(?=\s+(?:licensed?|licenced?|copyright|under)"
        r"|[.;,\n]|$)"
    ),
    (
        r"©\s*(?:\d{4}\s*)?(.+?)"
        r"(?=[.;,\n]|$)"
    ),
]


# ============================================================
# SELF AUTHORSHIP
# ============================================================


SELF_AUTHORSHIP_PATTERNS = [
    r"\bself[-\s]?authored\b",
    r"\bself[-\s]?created\b",
    r"\bself[-\s]?produced\b",
    r"\bmy own (?:image|photo|photograph|picture|work)\b",
    (
        r"\b(?:this|the) "
        r"(?:image|photo|photograph|picture) "
        r"is my own\b"
    ),
    (
        r"\b(?:image|photo|photograph|picture) "
        r"(?:created|taken|made|produced|photographed) "
        r"by me\b"
    ),
    (
        r"\bI "
        r"(?:created|took|made|produced|photographed) "
        r"(?:this|the) "
        r"(?:image|photo|photograph|picture)\b"
    ),
    r"\bowned by me\b",
    r"\bcopyright belongs to me\b",
]


# ============================================================
# SOURCE / REFERENCE ATTRIBUTION
# ============================================================


SOURCE_TEXT_PATTERNS = [
    r"\bsource\s*:",
    r"\bsource\b",
    r"\bimage source\s*:",
    r"\bimage source\b",
    r"\bphoto source\s*:",
    r"\bphoto source\b",
    r"\bimage from\b",
    r"\bphoto from\b",
    r"\bexternal image from\b",
    r"\bobtained from\b",
    r"\bsourced from\b",
    r"\bcourtesy of\b",
    r"\bcredit(?:ed)? to\b",
    r"\bimage courtesy of\b",
    r"\bphoto courtesy of\b",
    r"\breference\s*:",
    r"\breference\b",
    r"\bimage reference\b",
    r"\bphoto reference\b",
]


URL_PATTERN = re.compile(
    r"https?://[^\s<>'\"()]+",
    flags=re.IGNORECASE,
)


DOMAIN_PATTERN = re.compile(
    (
        r"\b(?:https?://)?(?:www\.)?"
        r"([A-Za-z0-9-]+"
        r"(?:\.[A-Za-z0-9-]+)+)"
        r"(?:/[^\s<>'\"]*)?"
    ),
    flags=re.IGNORECASE,
)


# ============================================================
# LICENCE / RIGHTS LINKS
# ============================================================


LICENCE_URL_MARKERS = [
    "creativecommons.org/licenses/",
    "creativecommons.org/publicdomain/",
    "pexels.com/license",
    "pexels.com/licence",
    "unsplash.com/license",
    "unsplash.com/licence",
    "pixabay.com/service/license",
    "pixabay.com/service/terms",
]


LICENCE_LINK_PATTERNS = [
    r"\blicen[cs]e\b",
    r"\blicen[cs]ing\b",
    r"\blicen[cs]e terms\b",
    r"\blicen[cs]e information\b",
    r"\bterms of the licen[cs]e\b",
]


RIGHTS_LINK_PATTERNS = [
    r"\bcopyright\b",
    r"\bcopyright information\b",
    r"\bright(?:s)?\b",
    r"\brights information\b",
    r"\busage rights\b",
    r"\bpermission\b",
    r"\bpermissions\b",
]


# ============================================================
# GENERAL HELPERS
# ============================================================


def _normalise_whitespace(
    value: str,
) -> str:
    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def _has_text(
    value: str | None,
) -> bool:
    return bool(
        value
        and value.strip()
    )


def _clean_author_name(
    value: str | None,
) -> str | None:
    if not value:
        return None

    cleaned = (
        _normalise_whitespace(
            value
        )
    )

    cleaned = re.sub(
        (
            r"\s+"
            r"(?:licensed?|licenced?|copyright|under)"
            r"\b.*$"
        ),
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

        return (
            _normalise_whitespace(
                value
            )
        )

    return None


def _contains_self_authorship_claim(
    text: str,
) -> bool:
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


# ============================================================
# PAGE IDENTITY
# ============================================================


def _extract_page_identity(
    soup: BeautifulSoup,
) -> str | None:
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

        if isinstance(
            content,
            str,
        ):
            content = (
                _normalise_whitespace(
                    content
                )
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

    if isinstance(
        author_rel,
        Tag,
    ):
        author_text = (
            author_rel.get_text(
                " ",
                strip=True,
            )
        )

        if author_text:
            return (
                _normalise_whitespace(
                    author_text
                )
            )

    return None


def _same_person(
    first: str | None,
    second: str | None,
) -> bool:
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


# ============================================================
# IMAGE MATCHING
# ============================================================


def _find_matching_img_tag(
    soup: BeautifulSoup,
    image: ImageRecord,
    base_url: str | None,
) -> Tag | None:
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


# ============================================================
# LOCAL CONTEXT
# ============================================================


def _is_small_local_container(
    container: Tag,
) -> bool:
    if container.name in {
        "html",
        "body",
        "main",
    }:
        return False

    return (
        len(
            container.find_all(
                "img"
            )
        )
        <= 1
    )


def _collect_local_tags(
    img_tag: Tag,
) -> list[Tag]:
    """
    Keep attribution evidence local to one image.

    The technical img element itself is not interpreted as
    attribution.

    Caption and nearby blocks are retained until another image
    or figure is reached.
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

        if sibling_count >= 3:
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


# ============================================================
# BASIC EVIDENCE
# ============================================================


def _extract_caption(
    img_tag: Tag,
) -> str | None:
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

    return (
        _normalise_whitespace(
            text
        )
    )


def _extract_nearby_text(
    tags: list[Tag],
) -> str:
    text_parts: list[str] = []

    for tag in tags:
        text = tag.get_text(
            " ",
            strip=True,
        )

        if not text:
            continue

        normalised = (
            _normalise_whitespace(
                text
            )
        )

        if (
            normalised
            and normalised
            not in text_parts
        ):
            text_parts.append(
                normalised
            )

    return " ".join(
        text_parts
    ).strip()


def _extract_image_attributes(
    img_tag: Tag,
) -> dict[str, str]:
    attributes: dict[
        str,
        str,
    ] = {}

    for key, value in img_tag.attrs.items():
        if isinstance(
            value,
            list,
        ):
            attributes[
                str(key)
            ] = " ".join(
                str(item)
                for item in value
            )

        elif value is None:
            attributes[
                str(key)
            ] = ""

        else:
            attributes[
                str(key)
            ] = str(
                value
            )

    return attributes


def _extract_image_html(
    img_tag: Tag,
) -> str:
    return str(
        img_tag
    )


def _extract_analysed_html_fragment(
    img_tag: Tag,
    tags: list[Tag],
) -> str:
    fragments: list[str] = []

    for tag in tags:
        html = str(
            tag
        )

        if html not in fragments:
            fragments.append(
                html
            )

    if not fragments:
        fragments.append(
            str(
                img_tag
            )
        )

    return "\n".join(
        fragments
    )


# ============================================================
# LINKS
# ============================================================


def _all_links(
    tags: list[Tag],
) -> list[Tag]:
    results: list[Tag] = []
    seen: set[int] = set()

    for tag in tags:
        if tag.name == "a":
            links = [tag]
        else:
            links = list(
                tag.find_all(
                    "a"
                )
            )

        for link in links:
            link_id = id(
                link
            )

            if link_id in seen:
                continue

            seen.add(
                link_id
            )

            results.append(
                link
            )

    return results


def _link_description(
    link: Tag,
) -> str:
    text = (
        link.get_text(
            " ",
            strip=True,
        )
    )

    title = link.get(
        "title",
        "",
    )

    if not isinstance(
        title,
        str,
    ):
        title = ""

    aria_label = link.get(
        "aria-label",
        "",
    )

    if not isinstance(
        aria_label,
        str,
    ):
        aria_label = ""

    return (
        _normalise_whitespace(
            " ".join(
                value
                for value in [
                    text,
                    title,
                    aria_label,
                ]
                if value
            )
        )
    )


# ============================================================
# URL HELPERS
# ============================================================


def _hostname(
    value: str | None,
) -> str | None:
    if not value:
        return None

    try:
        parsed = urlparse(
            value
        )
    except ValueError:
        return None

    hostname = parsed.hostname

    if not hostname:
        return None

    hostname = hostname.casefold()

    if hostname.startswith(
        "www."
    ):
        hostname = hostname[4:]

    return hostname


def _domain_from_text(
    text: str | None,
) -> str | None:
    if not text:
        return None

    match = DOMAIN_PATTERN.search(
        text
    )

    if not match:
        return None

    return (
        match.group(1)
        .casefold()
    )


def _url_from_text(
    text: str | None,
) -> str | None:
    """
    Return a URL explicitly written in visible text.
    """

    if not text:
        return None

    match = URL_PATTERN.search(
        text
    )

    if not match:
        return None

    return (
        match.group(0)
        .rstrip(
            ".,;:)]}"
        )
    )


def _contains_source_language(
    text: str,
) -> bool:
    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern in SOURCE_TEXT_PATTERNS
    )


def _is_licence_link(
    link: Tag,
) -> bool:
    """
    Return True when a link is clearly a licence-terms link.

    Such a link should be retained as licence evidence rather
    than being mistaken for a generic image source reference.
    """

    href = link.get(
        "href",
        "",
    )

    if not isinstance(
        href,
        str,
    ):
        href = ""

    description = (
        _link_description(
            link
        )
    )

    href_lower = (
        href.casefold()
    )

    if any(
        marker in href_lower
        for marker in LICENCE_URL_MARKERS
    ):
        return True

    return any(
        re.search(
            pattern,
            description,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern
        in LICENCE_LINK_PATTERNS
    )


def _is_rights_link(
    link: Tag,
) -> bool:
    description = (
        _link_description(
            link
        )
    )

    if not description:
        return False

    return any(
        re.search(
            pattern,
            description,
            flags=re.IGNORECASE,
        )
        is not None
        for pattern
        in RIGHTS_LINK_PATTERNS
    )


# ============================================================
# EXPLICIT SOURCE EXTRACTION
# ============================================================


def _extract_source_reference(
    image: ImageRecord,
    caption: str | None,
    nearby_text: str,
    tags: list[Tag],
    base_url: str | None,
) -> tuple[
    str | None,
    str | None,
    str | None,
    str | None,
]:
    """
    Extract a student-supplied source/reference.

    Accepted evidence includes:

    - Source: example.com
    - Image from example.com
    - Reference: https://example.com/image
    - a URL explicitly written in a caption or nearby
      attribution text;
    - a hyperlink explicitly associated with the image.

    CRITICAL:

    evidence.image.src is NEVER used as fallback attribution.

    Therefore this:

        <img src="image.jpg">

    or this:

        <img src="https://example.com/image.jpg">

    does not by itself create source evidence.
    """

    textual_sources = [
        (
            "figure caption",
            caption,
        ),
        (
            "nearby text",
            nearby_text,
        ),
        (
            "title attribute",
            image.title,
        ),
        (
            "alt attribute",
            image.alt,
        ),
    ]

    # ========================================================
    # 1. Explicit source wording
    # ========================================================

    for (
        source_label,
        source_text,
    ) in textual_sources:
        if not source_text:
            continue

        if not _contains_source_language(
            source_text
        ):
            continue

        explicit_url = (
            _url_from_text(
                source_text
            )
        )

        domain = (
            _domain_from_text(
                source_text
            )
        )

        return (
            domain,
            explicit_url,
            source_text,
            source_label,
        )

    # ========================================================
    # 2. Explicit URL written in caption / nearby text
    #
    # A URL written by the student as visible local text is
    # treated as a reference even if "Source:" is omitted.
    # ========================================================

    for (
        source_label,
        source_text,
    ) in (
        (
            "figure caption",
            caption,
        ),
        (
            "nearby text",
            nearby_text,
        ),
    ):
        if not source_text:
            continue

        explicit_url = (
            _url_from_text(
                source_text
            )
        )

        if not explicit_url:
            continue

        return (
            _hostname(
                explicit_url
            ),
            explicit_url,
            source_text,
            source_label,
        )

    # ========================================================
    # 3. Hyperlinks associated with the image
    # ========================================================

    for link in _all_links(
        tags
    ):
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

        # Licence and rights links belong to their own evidence
        # categories.
        if _is_licence_link(
            link
        ):
            continue

        if _is_rights_link(
            link
        ):
            continue

        resolved_url = (
            urljoin(
                base_url,
                href,
            )
            if base_url
            else href
        )

        # Ignore page-fragment navigation.
        if href.startswith(
            "#"
        ):
            continue

        description = (
            _link_description(
                link
            )
        )

        # If this is a creator profile link in a caption such
        # as Matheus Viana, author extraction handles ownership.
        # We retain it as source/reference only when the caption
        # or surrounding text clearly indicates image/source
        # attribution.
        context = (
            _normalise_whitespace(
                " ".join(
                    [
                        caption or "",
                        nearby_text or "",
                        description,
                    ]
                )
            )
        )

        if _contains_source_language(
            context
        ):
            return (
                _hostname(
                    resolved_url
                ),
                resolved_url,
                (
                    context
                    or description
                    or resolved_url
                ),
                (
                    "source hyperlink "
                    "associated with the image"
                ),
            )

        # A hyperlink directly inside a figcaption is itself
        # explicit image-associated information.
        parent = link.find_parent(
            "figcaption"
        )

        if isinstance(
            parent,
            Tag,
        ):
            caption_text = (
                _normalise_whitespace(
                    parent.get_text(
                        " ",
                        strip=True,
                    )
                )
            )

            return (
                _hostname(
                    resolved_url
                ),
                resolved_url,
                (
                    caption_text
                    or description
                    or resolved_url
                ),
                "figure caption hyperlink",
            )

    # ========================================================
    # 4. No explicit student-supplied reference
    # ========================================================

    return (
        None,
        None,
        None,
        None,
    )


# ============================================================
# LINKED CAPTION AUTHOR
# ============================================================


def _is_likely_licence_link_text(
    text: str,
) -> bool:
    lower = text.casefold()

    return any(
        marker in lower
        for marker in (
            "license",
            "licence",
            "creative commons",
            "terms",
            "permission",
        )
    )


def _extract_linked_caption_author(
    img_tag: Tag,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    """
    Detect linked creator names in figure captions.

    Supports:

    Image: "..." Matheus Viana
    Image: "..." by Matheus Viana
    Image by Student B
    Photo by Jane Smith
    """

    figure = img_tag.find_parent(
        "figure"
    )

    if not isinstance(
        figure,
        Tag,
    ):
        return (
            None,
            None,
            None,
        )

    figcaption = figure.find(
        "figcaption"
    )

    if not isinstance(
        figcaption,
        Tag,
    ):
        return (
            None,
            None,
            None,
        )

    caption_text = (
        _normalise_whitespace(
            figcaption.get_text(
                " ",
                strip=True,
            )
        )
    )

    if not caption_text:
        return (
            None,
            None,
            None,
        )

    for link in figcaption.find_all(
        "a"
    ):
        link_text = (
            _normalise_whitespace(
                link.get_text(
                    " ",
                    strip=True,
                )
            )
        )

        if not link_text:
            continue

        if _is_likely_licence_link_text(
            link_text
        ):
            continue

        escaped = re.escape(
            link_text
        )

        patterns = [
            rf"\bimage\s+by\s+{escaped}\b",
            rf"\bphoto\s+by\s+{escaped}\b",
            rf"\bphotograph\s+by\s+{escaped}\b",
            rf"\bcreated\s+by\s+{escaped}\b",
            rf"\bphotographed\s+by\s+{escaped}\b",
            rf"\bphotographer\s*:\s*{escaped}\b",
            rf"\bcreator\s*:\s*{escaped}\b",
            rf"\bcopyright\s*:\s*{escaped}\b",
            rf"©\s*{escaped}\b",
            (
                rf"\bimage\s*:\s*"
                rf"[\"“][^\"”]+[\"”]"
                rf"\s+by\s+"
                rf"{escaped}\b"
            ),
            (
                rf"\bimage\s*:\s*"
                rf"[\"“][^\"”]+[\"”]"
                rf"\s+"
                rf"{escaped}\b"
            ),
        ]

        if any(
            re.search(
                pattern,
                caption_text,
                flags=re.IGNORECASE,
            )
            for pattern in patterns
        ):
            return (
                link_text,
                caption_text,
                "figure caption",
            )

    return (
        None,
        None,
        None,
    )


# ============================================================
# AUTHOR EVIDENCE
# ============================================================


def _find_author_evidence(
    image: ImageRecord,
    caption: str | None,
    nearby_text: str,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    sources = [
        (
            "figure caption",
            caption,
        ),
        (
            "title attribute",
            image.title,
        ),
        (
            "alt attribute",
            image.alt,
        ),
        (
            "nearby text",
            nearby_text,
        ),
    ]

    for (
        source_name,
        source_text,
    ) in sources:
        if not source_text:
            continue

        raw_author = (
            _first_match(
                AUTHOR_PATTERNS,
                source_text,
            )
        )

        author = (
            _clean_author_name(
                raw_author
            )
        )

        if author:
            return (
                author,
                source_text,
                source_name,
            )

    return (
        None,
        None,
        None,
    )


# ============================================================
# LICENCE EVIDENCE
# ============================================================


def _find_licence_evidence(
    image: ImageRecord,
    caption: str | None,
    nearby_text: str,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    sources = [
        (
            "figure caption",
            caption,
        ),
        (
            "title attribute",
            image.title,
        ),
        (
            "alt attribute",
            image.alt,
        ),
        (
            "nearby text",
            nearby_text,
        ),
    ]

    for (
        source_name,
        source_text,
    ) in sources:
        if not source_text:
            continue

        licence = (
            _first_match(
                LICENCE_PATTERNS,
                source_text,
            )
        )

        if licence:
            return (
                licence,
                source_text,
                source_name,
            )

    return (
        None,
        None,
        None,
    )


# ============================================================
# LICENCE URL
# ============================================================


def _extract_licence_url(
    tags: list[Tag],
    base_url: str | None,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    for link in _all_links(
        tags
    ):
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

        description = (
            _link_description(
                link
            )
        )

        href_lower = (
            href.casefold()
        )

        recognised_url = any(
            marker in href_lower
            for marker in LICENCE_URL_MARKERS
        )

        labelled_licence = any(
            re.search(
                pattern,
                description,
                flags=re.IGNORECASE,
            )
            for pattern
            in LICENCE_LINK_PATTERNS
        )

        if not (
            recognised_url
            or labelled_licence
        ):
            continue

        resolved = (
            urljoin(
                base_url,
                href,
            )
            if base_url
            else href
        )

        return (
            resolved,
            (
                description
                or href
            ),
            (
                "licence hyperlink "
                "associated with the image"
            ),
        )

    return (
        None,
        None,
        None,
    )


# ============================================================
# RIGHTS URL
# ============================================================


def _extract_rights_link(
    tags: list[Tag],
    base_url: str | None,
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    for link in _all_links(
        tags
    ):
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

        description = (
            _link_description(
                link
            )
        )

        if not description:
            continue

        matches = any(
            re.search(
                pattern,
                description,
                flags=re.IGNORECASE,
            )
            for pattern
            in RIGHTS_LINK_PATTERNS
        )

        if not matches:
            continue

        resolved = (
            urljoin(
                base_url,
                href,
            )
            if base_url
            else href
        )

        return (
            resolved,
            description,
            (
                "copyright or rights hyperlink "
                "associated with the image"
            ),
        )

    return (
        None,
        None,
        None,
    )


# ============================================================
# COMBINED TEXT
# ============================================================


def _build_combined_text(
    image: ImageRecord,
    caption: str | None,
    nearby_text: str,
) -> str:
    values = [
        image.alt,
        image.title,
        caption,
        nearby_text,
    ]

    return " ".join(
        _normalise_whitespace(
            value
        )
        for value in values
        if isinstance(
            value,
            str,
        )
        and value.strip()
    )


# ============================================================
# MAIN EXTRACTOR
# ============================================================


def extract_attribution_evidence(
    parsed: ParsedHtml,
    images: list[ImageRecord],
) -> list[AttributionEvidence]:
    """
    Extract image-local copyright, source and licence evidence.

    The technical image.src identifies the image but is not
    automatically promoted to attribution evidence.

    A separate URL, hyperlink, website name or source/reference
    statement explicitly associated with the image may become
    source evidence.
    """

    soup = BeautifulSoup(
        parsed.html,
        "lxml",
    )

    page_identity = (
        _extract_page_identity(
            soup
        )
    )

    results: list[
        AttributionEvidence
    ] = []

    for original_image in images:
        image = original_image

        img_tag = (
            _find_matching_img_tag(
                soup,
                image,
                parsed.base_url,
            )
        )

        local_tags: list[Tag] = []

        caption: str | None = None
        nearby_text = ""

        image_html: str | None = None

        analysed_html_fragment: (
            str | None
        ) = None

        if img_tag is not None:
            local_tags = (
                _collect_local_tags(
                    img_tag
                )
            )

            caption = (
                _extract_caption(
                    img_tag
                )
            )

            nearby_text = (
                _extract_nearby_text(
                    local_tags
                )
            )

            image_html = (
                _extract_image_html(
                    img_tag
                )
            )

            analysed_html_fragment = (
                _extract_analysed_html_fragment(
                    img_tag,
                    local_tags,
                )
            )

            image = image.model_copy(
                update={
                    "attributes": (
                        _extract_image_attributes(
                            img_tag
                        )
                    )
                }
            )

        # =====================================================
        # CREATOR / COPYRIGHT HOLDER
        # =====================================================

        (
            possible_author,
            author_evidence_text,
            author_evidence_source,
        ) = _find_author_evidence(
            image,
            caption,
            nearby_text,
        )

        if (
            not possible_author
            and img_tag is not None
        ):
            (
                linked_author,
                linked_text,
                linked_source,
            ) = (
                _extract_linked_caption_author(
                    img_tag
                )
            )

            if linked_author:
                possible_author = (
                    linked_author
                )

                author_evidence_text = (
                    linked_text
                )

                author_evidence_source = (
                    linked_source
                )

        # =====================================================
        # EXPLICIT SOURCE / REFERENCE
        # =====================================================

        (
            source_name,
            source_url,
            source_evidence_text,
            source_evidence_source,
        ) = _extract_source_reference(
            image=image,
            caption=caption,
            nearby_text=nearby_text,
            tags=local_tags,
            base_url=parsed.base_url,
        )

        # =====================================================
        # LICENCE
        # =====================================================

        (
            licence_name,
            licence_evidence_text,
            licence_evidence_source,
        ) = _find_licence_evidence(
            image,
            caption,
            nearby_text,
        )

        # =====================================================
        # LICENCE TERMS LOCATION
        # =====================================================

        (
            licence_url,
            licence_url_evidence_text,
            licence_url_evidence_source,
        ) = _extract_licence_url(
            local_tags,
            parsed.base_url,
        )

        # =====================================================
        # RIGHTS LINK
        # =====================================================

        (
            rights_url,
            rights_evidence_text,
            rights_evidence_source,
        ) = _extract_rights_link(
            local_tags,
            parsed.base_url,
        )

        # =====================================================
        # SELF AUTHORSHIP
        # =====================================================

        combined_text = (
            _build_combined_text(
                image,
                caption,
                nearby_text,
            )
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
            not licence_name
            and named_page_author_claim
        ):
            licence_name = (
                SELF_AUTHORED_LICENCE
            )

            licence_evidence_text = (
                caption
                or author_evidence_text
                or combined_text
            )

            licence_evidence_source = (
                "self-authorship statement"
            )

        if (
            explicit_self_claim
            and not licence_name
        ):
            licence_name = (
                SELF_AUTHORED_LICENCE
            )

            licence_evidence_text = (
                combined_text
            )

            licence_evidence_source = (
                "self-authorship statement"
            )

        if (
            explicit_self_claim
            and not possible_author
            and page_identity
        ):
            possible_author = (
                page_identity
            )

            author_evidence_text = (
                combined_text
            )

            author_evidence_source = (
                "self-authorship claim and page identity"
            )

        # =====================================================
        # SELF-AUTHORED LICENCE TERMS
        # =====================================================

        if (
            licence_name
            and licence_name.casefold()
            == SELF_AUTHORED_LICENCE.casefold()
        ):
            licence_url = None

            licence_url_evidence_text = (
                None
            )

            licence_url_evidence_source = (
                None
            )

        # =====================================================
        # RESULT
        # =====================================================

        results.append(
            AttributionEvidence(
                image=image,

                nearby_text=nearby_text,

                caption=caption,

                possible_author=(
                    possible_author
                ),

                author_evidence_text=(
                    author_evidence_text
                ),

                author_evidence_source=(
                    author_evidence_source
                ),

                source_name=(
                    source_name
                ),

                source_url=(
                    source_url
                ),

                source_evidence_text=(
                    source_evidence_text
                ),

                source_evidence_source=(
                    source_evidence_source
                ),

                licence_name=(
                    licence_name
                ),

                licence_evidence_text=(
                    licence_evidence_text
                ),

                licence_evidence_source=(
                    licence_evidence_source
                ),

                licence_url=(
                    licence_url
                ),

                licence_url_evidence_text=(
                    licence_url_evidence_text
                ),

                licence_url_evidence_source=(
                    licence_url_evidence_source
                ),

                rights_url=(
                    rights_url
                ),

                rights_evidence_text=(
                    rights_evidence_text
                ),

                rights_evidence_source=(
                    rights_evidence_source
                ),

                image_html=(
                    image_html
                ),

                analysed_html_fragment=(
                    analysed_html_fragment
                ),
            )
        )

    return results