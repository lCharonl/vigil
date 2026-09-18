"""Tests for the detection pipeline orchestration."""

from datetime import UTC, datetime

from vigil.detect.pipeline import detect_event
from vigil.detect.registry import Rule
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
    event = make_event(["apple.com", "microsoft.secure-a-b-c-d.com"])
    detections = detect_event(event, watched=frozenset({"microsoft"}))
    assert len(detections) == 1
    domain, reasons = detections[0]
    assert domain == "microsoft.secure-a-b-c-d.com"
    assert {r.rule for r in reasons} == {Rule.R_01, Rule.M_01}


def test_detect_event_no_match_returns_empty():
    assert detect_event(make_event(["apple.com"])) == []


def test_detect_event_morphological_alone_is_suppressed():
    # M-01 (3+ hyphens) matches but nothing else does: too weak alone.
    event = make_event(["secure-a-b-c-d.com"])
    assert detect_event(event) == []


def test_detect_event_morphological_kept_when_reinforced():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    detections = detect_event(event, watched=frozenset({"microsoft"}))
    assert len(detections) == 1
    _domain, reasons = detections[0]
    assert Rule.M_01 in [r.rule for r in reasons]
    assert Rule.R_01 in [r.rule for r in reasons]


def test_detect_event_applies_digit_exceptions():
    # office365.com alone: M-04 would match but is suppressed (no reinforcement).
    event = make_event(["office365.com"])
    assert detect_event(event) == []

    # reinforced by R-01: M-04 (without exceptions) is kept, then suppressed by exceptions.
    reinforced = make_event(["microsoft.office365-login.com"])
    assert detect_event(reinforced, watched=frozenset({"microsoft"})) != []
    detections = detect_event(
        reinforced, frozenset({"365"}), watched=frozenset({"microsoft"})
    )
    assert Rule.M_04 not in [r.rule for _domain, reasons in detections for r in reasons]


def test_detect_event_referential_via_pipeline():
    event = make_event(["microsoft.login-example.com"])
    detections = detect_event(event, watched=frozenset({"microsoft"}))
    assert len(detections) == 1
    domain, reasons = detections[0]
    assert domain == "microsoft.login-example.com"
    assert Rule.R_01 in [r.rule for r in reasons]


def test_detect_event_allowlist_suppresses_detection():
    # reinforced detection (R-01 + M-03) on cisco's own legitimate infra
    event = make_event(["microsoft.b08cf4.vpn.sse.cisco.com"])
    assert detect_event(event, watched=frozenset({"microsoft"})) != []
    assert (
        detect_event(event, watched=frozenset({"microsoft"}), allowlist=frozenset({"cisco.com"}))
        == []
    )


def test_detect_event_allowlist_only_suppresses_matching_domains():
    event = make_event(
        ["microsoft.b08cf4.vpn.sse.cisco.com", "microsoft.secure-a-b-c-d.com"]
    )
    detections = detect_event(
        event, watched=frozenset({"microsoft"}), allowlist=frozenset({"cisco.com"})
    )
    assert len(detections) == 1
    assert detections[0][0] == "microsoft.secure-a-b-c-d.com"
