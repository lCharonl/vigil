"""Tests for the morphological family and shared name decomposition."""

from vigil.detect.families.morphological import (
    evaluate_morphological,
    has_digit_run,
    has_min_hyphens,
    has_min_labels,
    numeric_exceptions,
    registrable_too_long,
)
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.names import parse_domain


def test_parse_domain_multi_label_suffix():
    name = parse_domain("login.micro.foo.co.uk")
    assert name.registrable == "foo.co.uk"
    assert name.suffix == "co.uk"
    assert name.labels == ("login", "micro", "foo", "co", "uk")


def test_m01_hyphen_threshold():
    assert not has_min_hyphens(parse_domain("a-b-c.com"))  # 2 hyphens
    assert has_min_hyphens(parse_domain("a-b-c-d.com"))  # 3 hyphens


def test_m02_registrable_length():
    assert not registrable_too_long(parse_domain(f"{'a' * 36}.com"))  # 40 chars
    assert registrable_too_long(parse_domain(f"{'a' * 37}.com"))  # 41 chars


def test_m03_label_count():
    assert not has_min_labels(parse_domain("a.b.com"))  # 3 labels
    assert has_min_labels(parse_domain("a.b.c.com"))  # 4 labels


def test_m04_digit_run_threshold():
    assert not has_digit_run(parse_domain("ab12.com"))  # 2 digits
    assert has_digit_run(parse_domain("ab123.com"))  # 3 digits


def test_m04_exception_suppresses_single_run():
    name = parse_domain("office365.com")
    assert has_digit_run(name)
    assert not has_digit_run(name, exceptions=frozenset({"365"}))


def test_m04_exception_keeps_other_runs():
    name = parse_domain("office365-auth-92834.net")
    assert has_digit_run(name, exceptions=frozenset({"365"}))  # 92834 remains


def test_numeric_exceptions_from_domains():
    assert numeric_exceptions(["office365.com", "n26.com"]) == frozenset({"365"})


def test_evaluate_first_match_wins():
    # matches M-01 (hyphens) and M-02 (length); M-01 comes first
    reason = evaluate_morphological(parse_domain("secure-microsoft-login-account.com"))
    assert reason is not None
    assert reason.family == Family.MORPHOLOGICAL
    assert reason.rule == Rule.M_01


def test_evaluate_no_match_returns_none():
    assert evaluate_morphological(parse_domain("apple.com")) is None


def test_evaluate_m04_exception_yields_no_reason():
    name = parse_domain("office365.com")
    assert evaluate_morphological(name, numeric_exceptions(["office365.com"])) is None
