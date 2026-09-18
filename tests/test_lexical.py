"""Tests for the lexical family."""

from vigil.detect.families.lexical import (
    document_term_present,
    evaluate_lexical,
    generic_term_present,
    mfa_term_present,
    www_as_domain_component,
)
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.names import parse_domain

MFA_TERMS = frozenset({"mfa"})
DOCUMENT_TERMS = frozenset({"invoice"})
GENERIC_TERMS = frozenset({"login"})


def test_l01_mfa_term_in_registrable_core():
    name = parse_domain("mfa-example.com")
    assert mfa_term_present(name, MFA_TERMS)


def test_l01_no_match_without_term():
    name = parse_domain("secure-example.com")
    assert not mfa_term_present(name, MFA_TERMS)


def test_l02_document_term_in_registrable_core():
    name = parse_domain("invoice-example.com")
    assert document_term_present(name, DOCUMENT_TERMS)


def test_l02_no_match_without_term():
    name = parse_domain("contract-example.com")
    assert not document_term_present(name, frozenset({"esign"}))


def test_l03_www_as_domain_component():
    name = parse_domain("www-example-login.com")
    assert www_as_domain_component(name)


def test_l03_no_match_when_www_is_the_real_subdomain():
    name = parse_domain("www.example.com")
    assert not www_as_domain_component(name)


def test_l03_no_match_without_www():
    name = parse_domain("example-login.com")
    assert not www_as_domain_component(name)


def test_l04_generic_term_in_registrable_core():
    name = parse_domain("login-example.com")
    assert generic_term_present(name, GENERIC_TERMS)


def test_l04_no_match_without_term():
    name = parse_domain("example.com")
    assert not generic_term_present(name, GENERIC_TERMS)


def test_evaluate_first_match_wins():
    # "mfa" (L-01) and "login" (L-04) both present; L-01 comes first
    name = parse_domain("mfa-login-example.com")
    terms = {Rule.L_01: MFA_TERMS, Rule.L_04: GENERIC_TERMS}
    reason = evaluate_lexical(name, terms)
    assert reason is not None
    assert reason.family == Family.LEXICAL
    assert reason.rule == Rule.L_01


def test_evaluate_no_terms_returns_none():
    name = parse_domain("mfa-example.com")
    assert evaluate_lexical(name) is None


def test_evaluate_structural_rule_needs_no_terms():
    name = parse_domain("www-example-login.com")
    reason = evaluate_lexical(name)
    assert reason is not None
    assert reason.rule == Rule.L_03


def test_evaluate_respects_rules_filter():
    name = parse_domain("mfa-login-example.com")
    terms = {Rule.L_01: MFA_TERMS, Rule.L_04: GENERIC_TERMS}
    assert evaluate_lexical(name, terms, rules=frozenset({Rule.L_04})).rule == Rule.L_04
    assert evaluate_lexical(name, terms, rules=frozenset({Rule.L_02})) is None
