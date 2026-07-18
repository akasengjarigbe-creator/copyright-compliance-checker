from app.knowledgebase.licence_loader import (
    load_licence_knowledge_base,
    get_licence_rules,
)


def test_loads_licence_knowledge_base():
    knowledge_base = load_licence_knowledge_base()

    assert "CC BY 4.0" in knowledge_base
    assert "CC BY-NC 4.0" in knowledge_base
    assert "CC BY-ND 4.0" in knowledge_base


def test_gets_cc_by_nc_rules():
    rules = get_licence_rules("CC BY-NC 4.0")

    assert rules is not None
    assert rules["commercial_use"] is False
    assert rules["modification"] is True
    assert rules["requires_attribution"] is True


def test_gets_cc_by_nd_rules():
    rules = get_licence_rules("CC BY-ND 4.0")

    assert rules is not None
    assert rules["commercial_use"] is True
    assert rules["modification"] is False
    assert rules["requires_no_derivatives"] is True


def test_licence_lookup_is_case_insensitive():
    rules = get_licence_rules("cc by 4.0")

    assert rules is not None
    assert rules["commercial_use"] is True


def test_unknown_licence_returns_none():
    rules = get_licence_rules("Unknown Licence")

    assert rules is None