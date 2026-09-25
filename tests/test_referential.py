"""Tests for the referential family and bounded Levenshtein distance."""

from vigil.detect.families.referential import (
    brand_adjacent_to_auth_term,
    brand_followed_by_tld_token,
    brand_outside_registrable,
    brand_typo_distance,
    evaluate_referential,
)
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.levenshtein import bounded_levenshtein
from vigil.detect.techniques.names import parse_domain

MICROSOFT = frozenset({"microsoft"})
PAYPAL = frozenset({"paypal"})
AMAZON = frozenset({"amazon"})
AUTH_TERMS = frozenset({"login"})


def test_r01_brand_in_subdomain_not_registrable():
    name = parse_domain("microsoft.login-example.com")
    assert brand_outside_registrable(name, MICROSOFT)


def test_r01_no_match_when_brand_also_in_registrable():
    name = parse_domain("microsoft.microsoft-help.com")
    assert not brand_outside_registrable(name, MICROSOFT)


def test_r01_no_match_when_no_subdomain():
    assert not brand_outside_registrable(parse_domain("microsoft.com"), MICROSOFT)


def test_r02_brand_followed_by_tld_token():
    name = parse_domain("paypal-com-login.info")
    assert brand_followed_by_tld_token(name, PAYPAL)


def test_r02_no_match_when_tld_token_precedes_brand():
    name = parse_domain("com-paypal-login.info")
    assert not brand_followed_by_tld_token(name, PAYPAL)


def test_r03_within_threshold():
    assert brand_typo_distance(parse_domain("micros0ft.com"), MICROSOFT)
    assert brand_typo_distance(parse_domain("arnazon.net"), AMAZON)


def test_r03_exceeds_threshold():
    assert not brand_typo_distance(parse_domain("mmiiccrroosoft.com"), MICROSOFT)


def test_r03_exact_match_not_flagged():
    assert not brand_typo_distance(parse_domain("microsoft.com"), MICROSOFT)


def test_r03_short_brand_uses_tighter_distance():
    # "axa" (3 chars) at distance 2 from unrelated words is pure coincidence;
    # the short-brand budget of 1 must reject them.
    axa = frozenset({"axa"})
    assert not brand_typo_distance(parse_domain("data.com"), axa)
    assert not brand_typo_distance(parse_domain("meta.com"), axa)


def test_r03_short_brand_still_catches_single_edit_typo():
    axa = frozenset({"axa"})
    assert brand_typo_distance(parse_domain("axaa.com"), axa)  # single insertion, distance 1


def test_r04_brand_adjacent_to_auth_term():
    name = parse_domain("paypal-login.net")
    assert brand_adjacent_to_auth_term(name, PAYPAL, AUTH_TERMS)


def test_r04_reversed_order_still_matches():
    name = parse_domain("login-paypal.net")
    assert brand_adjacent_to_auth_term(name, PAYPAL, AUTH_TERMS)


def test_evaluate_first_match_wins():
    # "paypal" outside the registrable (R-01) and "arnazon" is a typo of "amazon" (R-03)
    # both match; R-01 comes first in evaluation order
    name = parse_domain("paypal.arnazon.net")
    reason = evaluate_referential(name, frozenset({"paypal", "amazon"}))
    assert reason is not None
    assert reason.family == Family.REFERENTIAL
    assert reason.rule == Rule.R_01


def test_evaluate_no_match_returns_none():
    name = parse_domain("paypal-login.net")
    assert evaluate_referential(name, PAYPAL, {Rule.R_04: frozenset()}) is None
    assert evaluate_referential(parse_domain("apple.com"), PAYPAL, {Rule.R_04: AUTH_TERMS}) is None


def test_evaluate_empty_watched_returns_none():
    assert evaluate_referential(parse_domain("paypal-login.net")) is None


def test_bounded_levenshtein_exact_match():
    assert bounded_levenshtein("microsoft", "microsoft", 2) == 0


def test_bounded_levenshtein_single_edits():
    assert bounded_levenshtein("micros0ft", "microsoft", 2) == 1  # substitution
    assert bounded_levenshtein("microsof", "microsoft", 2) == 1  # deletion
    assert bounded_levenshtein("microsofpt", "microsoft", 2) == 1  # insertion
    assert bounded_levenshtein("micorsoft", "microsoft", 2) == 2  # adjacent swap, no transposition


def test_bounded_levenshtein_beyond_max_returns_none():
    assert bounded_levenshtein("mmiiccrroosoft", "microsoft", 2) is None
