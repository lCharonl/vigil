"""Tests for the morphological family and shared name decomposition."""

from vigil.detect.families.morphological import (
    evaluate_morphological,
    has_digit_run,
    has_min_hyphens,
    has_min_labels,
    numeric_exceptions,
)
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.names import parse_domain


def test_parse_domain_multi_label_suffix():
    name = parse_domain("login.micro.foo.co.uk")
    assert name.registrable == "foo.co.uk"
    assert name.suffix == "co.uk"
    assert name.labels == ("login", "micro", "foo", "co", "uk")


def test_parse_domain_psl_private_suffix():
    # pages.dev is a PaaS suffix (PSL private section): the customer subdomain is the
    # registrable domain, not "pages" mistakenly split off "dev"
    name = parse_domain("beargummy.pages.dev")
    assert name.registrable == "beargummy.pages.dev"
    assert name.suffix == "pages.dev"
    assert name.subdomain == ""


def test_m01_hyphen_threshold():
    assert not has_min_hyphens(parse_domain("a-b-c.com"))  # 2 hyphens
    assert has_min_hyphens(parse_domain("a-b-c-d.com"))  # 3 hyphens


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


def test_evaluate_returns_every_matching_rule():
    # matches M-01 (hyphens) and M-03 (labels)
    reasons = evaluate_morphological(parse_domain("a-b-c-d.e.f.com"))
    assert [r.rule for r in reasons] == [Rule.M_01, Rule.M_03]
    assert all(r.family == Family.MORPHOLOGICAL for r in reasons)


def test_evaluate_no_match_returns_empty():
    assert evaluate_morphological(parse_domain("apple.com")) == []


def test_evaluate_m04_exception_yields_no_reason():
    name = parse_domain("office365.com")
    assert evaluate_morphological(name, numeric_exceptions(["office365.com"])) == []
