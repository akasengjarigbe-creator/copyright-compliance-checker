import json
import re
from pathlib import Path
from typing import Any


LICENCE_FILE = Path(__file__).with_name("licences.json")


BUILT_IN_LICENCES: dict[str, dict[str, Any]] = {
    "Pexels License": {
        "commercial_use": True,
        "modification": True,
        "requires_share_alike": False,
        "attribution_required": False,
    },
    "Unsplash License": {
        "commercial_use": True,
        "modification": True,
        "requires_share_alike": False,
        "attribution_required": False,
    },
    "Pixabay Content License": {
        "commercial_use": True,
        "modification": True,
        "requires_share_alike": False,
        "attribution_required": False,
    },
    "Self-authored claim": {
        "commercial_use": True,
        "modification": True,
        "requires_share_alike": False,
        "attribution_required": False,
    },
}


LICENCE_ALIASES = {
    "pexels": "Pexels License",
    "pexels licence": "Pexels License",
    "pexels license": "Pexels License",
    "unsplash": "Unsplash License",
    "unsplash licence": "Unsplash License",
    "unsplash license": "Unsplash License",
    "pixabay": "Pixabay Content License",
    "pixabay licence": "Pixabay Content License",
    "pixabay license": "Pixabay Content License",
    "pixabay content licence": "Pixabay Content License",
    "pixabay content license": "Pixabay Content License",
    "self authored": "Self-authored claim",
    "self-authored": "Self-authored claim",
    "self-authored claim": "Self-authored claim",
}


def _normalise_licence_name(
    licence_name: str,
) -> str:
    """
    Normalise a licence name for reliable comparison.
    """

    value = licence_name.strip().casefold()

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


def load_licence_knowledge_base() -> dict[str, dict[str, Any]]:
    """
    Load the JSON knowledge base and merge the built-in
    platform-licence definitions.
    """

    knowledge_base: dict[str, dict[str, Any]] = {}

    if LICENCE_FILE.exists():
        with LICENCE_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            knowledge_base = json.load(file)

    for name, rules in BUILT_IN_LICENCES.items():
        knowledge_base.setdefault(
            name,
            rules,
        )

    return knowledge_base


def get_licence_rules(
    licence_name: str | None,
) -> dict[str, Any] | None:
    """
    Return the rules for a recognised licence.

    Licence names and common aliases are compared
    case-insensitively.
    """

    if not licence_name:
        return None

    normalised_name = _normalise_licence_name(
        licence_name
    )

    canonical_name = LICENCE_ALIASES.get(
        normalised_name,
        licence_name.strip(),
    )

    knowledge_base = load_licence_knowledge_base()

    canonical_normalised = _normalise_licence_name(
        canonical_name
    )

    for stored_name, rules in knowledge_base.items():
        if (
            _normalise_licence_name(stored_name)
            == canonical_normalised
        ):
            return rules

    return None