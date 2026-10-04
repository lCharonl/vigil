"""Tests for the wildcard filter."""

from datetime import UTC, datetime

from vigil.ingest.filters import is_wildcard, strip_long_domains, strip_wildcards
from vigil.models import CertEvent


def make_event(domains: list[str]) -> CertEvent:
    return CertEvent(
        serial_number="01",
        signature_algo="sha256WithRSAEncryption",
        issuer_common_name="R11",
        validity_not_before=datetime(2025, 1, 1, tzinfo=UTC),
        validity_not_after=datetime(2025, 4, 1, tzinfo=UTC),
        domains=domains,
        source="test",
        is_precert=False,
    )


def test_is_wildcard():
    assert is_wildcard("*.xxx.com")
    assert not is_wildcard("xxx.com")
    assert not is_wildcard("www.xxx.com")


def test_strip_wildcards_mixed_keeps_non_wildcard():
    event = strip_wildcards(make_event(["*.acme-cloud.io", "acme-cloud.io"]))
    assert event is not None
    assert event.domains == ["acme-cloud.io"]


def test_strip_wildcards_all_wildcard_returns_none():
    assert strip_wildcards(make_event(["*.foo.com"])) is None


def test_strip_wildcards_no_wildcard_is_unchanged():
    event = strip_wildcards(make_event(["a.com", "b.com"]))
    assert event is not None
    assert event.domains == ["a.com", "b.com"]


def test_strip_long_domains_keeps_boundary_length():
    domain = "a" * 36 + ".com"  # 40 chars
    event = strip_long_domains(make_event([domain]), 40)
    assert event is not None
    assert event.domains == [domain]


def test_strip_long_domains_drops_over_limit():
    long = "a" * 37 + ".com"  # 41 chars
    event = strip_long_domains(make_event([long, "ok.com"]), 40)
    assert event is not None
    assert event.domains == ["ok.com"]


def test_strip_long_domains_all_long_returns_none():
    assert strip_long_domains(make_event(["a" * 41 + ".com"]), 40) is None
