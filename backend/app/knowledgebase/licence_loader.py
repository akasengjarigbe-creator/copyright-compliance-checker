import json
from pathlib import Path
from typing import Any


LICENCE_FILE = Path(__file__).with_name("licences.json")


def load_licence_knowledge_base() -> dict[str, dict[str, Any]]:
    """
    Load the licence knowledge base from licences.json.

    Returns:
        A dictionary whose keys are licence names and whose values
        contain the permissions and restrictions for each licence.
    """
    with LICENCE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_licence_rules(
    licence_name: str | None
) -> dict[str, Any] | None:
    """
    Return the rules for one licence.

    The comparison is case-insensitive so values such as
    'cc by 4.0' and 'CC BY 4.0' are treated as the same licence.
    """
    if not licence_name:
        return None

    knowledge_base = load_licence_knowledge_base()
    normalised_name = licence_name.strip().upper()

    for stored_name, rules in knowledge_base.items():
        if stored_name.upper() == normalised_name:
            return rules

    return None