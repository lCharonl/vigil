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


def test_evaluate_mixed_script_wins_over_punycode():
    name = parse_domain("xn--pypal-4ve.com")
    reason = evaluate_encoding(name)
    assert reason is not None
    assert reason.family == Family.ENCODING
    assert reason.rule == Rule.E_01


def test_evaluate_punycode_only():
    name = parse_domain("xn--80ak6aa92e.com")
    reason = evaluate_encoding(name)
    assert reason is not None
    assert reason.rule == Rule.E_02


def test_evaluate_no_match_returns_none():
    assert evaluate_encoding(parse_domain("microsoft.com")) is None


def test_evaluate_respects_rule_restriction():
    name = parse_domain("xn--pypal-4ve.com")
    assert evaluate_encoding(name, rules=frozenset({Rule.E_02})) is not None
    assert evaluate_encoding(name, rules=frozenset()) is None
