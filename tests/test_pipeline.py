"""Tests for the detection pipeline orchestration."""

from datetime import UTC, datetime

from vigil.detect.pipeline import detect_event
from vigil.detect.rules import Rule
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


def test_detect_event_keeps_only_matching_domains():
    event = make_event(["apple.com", "secure-a-b-c-d.com"])
    detections = detect_event(event)
    assert len(detections) == 1
    domain, reasons = detections[0]
    assert domain == "secure-a-b-c-d.com"
    assert [r.rule for r in reasons] == [Rule.M_01]


def test_detect_event_no_match_returns_empty():
    assert detect_event(make_event(["apple.com"])) == []


def test_detect_event_applies_digit_exceptions():
    event = make_event(["office365.com"])
    assert detect_event(event) != []  # M-04 without exceptions
    assert detect_event(event, frozenset({"365"})) == []  # suppressed
