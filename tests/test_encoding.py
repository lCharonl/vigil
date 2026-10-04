"""Tests for the encoding family."""

from vigil.detect.families.encoding import (
    evaluate_encoding,
    has_mixed_script_label,
    has_punycode_label,
)
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.names import parse_domain


def test_e01_mixed_latin_cyrillic_label():
    # "xn--pypal-4ve" decodes to "pаypal" (Cyrillic "а" mixed with Latin letters)
    name = parse_domain("xn--pypal-4ve.com")
    assert has_mixed_script_label(name)


def test_e01_no_match_for_plain_ascii():
    assert not has_mixed_script_label(parse_domain("microsoft.com"))


def test_e01_no_match_for_pure_cyrillic_label():
    # "xn--80ak6aa92e" decodes to "аррӏе": all Cyrillic, no script mixing
    assert not has_mixed_script_label(parse_domain("xn--80ak6aa92e.com"))


def test_e02_punycode_label():
    assert has_punycode_label(parse_domain("xn--e1aybc.com"))


def test_e02_no_match_for_plain_ascii():
    assert not has_punycode_label(parse_domain("microsoft.com"))


def test_evaluate_mixed_script_and_punycode_both_reported():
    name = parse_domain("xn--pypal-4ve.com")
    reasons = evaluate_encoding(name)
    assert [r.rule for r in reasons] == [Rule.E_01, Rule.E_02]
    assert all(r.family == Family.ENCODING for r in reasons)


def test_evaluate_punycode_only():
    name = parse_domain("xn--80ak6aa92e.com")
    assert [r.rule for r in evaluate_encoding(name)] == [Rule.E_02]


def test_evaluate_no_match_returns_empty():
    assert evaluate_encoding(parse_domain("microsoft.com")) == []


def test_evaluate_respects_rule_restriction():
    name = parse_domain("xn--pypal-4ve.com")
    assert evaluate_encoding(name, rules=frozenset({Rule.E_02})) != []
    assert evaluate_encoding(name, rules=frozenset()) == []
