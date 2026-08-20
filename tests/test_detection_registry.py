"""Registry parity and lexical-term loading tests."""

import re
from pathlib import Path

from vigil.detect.rules import RULE_FAMILY, TERM_RULES, Rule, load_terms

DOC = Path(__file__).resolve().parent.parent / "docs" / "detections_rules.md"


def test_every_doc_rule_id_is_registered():
    ids = set(re.findall(r"\b[A-Z]-\d{2}\b", DOC.read_text(encoding="utf-8")))
    registered = {r.value for r in Rule}
    assert ids <= registered, f"unregistered ids: {ids - registered}"


def test_every_rule_has_a_family():
    assert set(RULE_FAMILY) == set(Rule)


def test_term_rules_have_non_empty_lists():
    terms = load_terms()
    for rule in TERM_RULES:
        assert terms.get(rule), f"missing terms for {rule.value}"


def test_loaded_terms_are_lowercased():
    terms = load_terms()
    for words in terms.values():
        assert all(w == w.lower() for w in words)
