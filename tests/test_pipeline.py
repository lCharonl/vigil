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


POINTS = {rule: (5 if rule.value.startswith("M-") else 50) for rule in Rule}


def test_detect_event_reasons_carry_rule_points():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    detections = detect_event(event, watched=frozenset({"microsoft"}), points=POINTS)
    _domain, reasons = detections[0]
    assert {(r.rule, r.points) for r in reasons} == {(Rule.R_01, 50), (Rule.M_01, 5)}


def test_detect_event_without_points_scores_zero():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    _domain, reasons = detect_event(event, watched=frozenset({"microsoft"}))[0]
    assert all(r.points == 0 for r in reasons)


def test_detect_event_below_threshold_is_dropped():
    # M-01 (3+ hyphens) alone: 5 points
    event = make_event(["secure-a-b-c-d.com"])
    assert detect_event(event, points=POINTS, score_threshold=50) == []


def test_detect_event_score_equal_to_threshold_is_kept():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    detections = detect_event(
        event, watched=frozenset({"microsoft"}), points=POINTS, score_threshold=55
    )
    assert len(detections) == 1
    assert detect_event(
        event, watched=frozenset({"microsoft"}), points=POINTS, score_threshold=56
    ) == []


def test_detect_event_zero_threshold_keeps_morphological_alone():
    event = make_event(["secure-a-b-c-d.com"])
    detections = detect_event(event, points=POINTS)
    assert [r.rule for _domain, reasons in detections for r in reasons] == [Rule.M_01]


def test_detect_event_points_restrict_rules():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    detections = detect_event(event, watched=frozenset({"microsoft"}), points={Rule.M_01: 5})
    assert [r.rule for _domain, reasons in detections for r in reasons] == [Rule.M_01]


def test_detect_event_applies_digit_exceptions():
    event = make_event(["microsoft.office365-login.com"])
    watched = frozenset({"microsoft"})
    rules_seen = [r.rule for _d, reasons in detect_event(event, watched=watched) for r in reasons]
    assert Rule.M_04 in rules_seen
    detections = detect_event(event, frozenset({"365"}), watched=watched)
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


def test_detect_event_lexical_alone_is_kept():
    event = make_event(["mfa-example.com"])
    detections = detect_event(event, terms={Rule.L_01: frozenset({"mfa"})})
    assert len(detections) == 1
    _domain, reasons = detections[0]
    assert [r.rule for r in reasons] == [Rule.L_01]


def test_detect_event_lexical_reinforces_morphological():
    event = make_event(["secure-login-verify-my.example.com"])
    detections = detect_event(event, terms={Rule.L_04: frozenset({"login"})})
    assert len(detections) == 1
    _domain, reasons = detections[0]
    assert {r.rule for r in reasons} == {Rule.L_04, Rule.M_01}


def test_detect_event_allowlist_only_suppresses_matching_domains():
    event = make_event(
        ["microsoft.b08cf4.vpn.sse.cisco.com", "microsoft.secure-a-b-c-d.com"]
    )
    detections = detect_event(
        event, watched=frozenset({"microsoft"}), allowlist=frozenset({"cisco.com"})
    )
    assert len(detections) == 1
    assert detections[0][0] == "microsoft.secure-a-b-c-d.com"


def test_detect_event_tranco_suppresses_by_registrable_domain():
    event = make_event(["almost-bank-a-b-c-d.alegra.com", "microsoft.secure-a-b-c-d.com"])
    detections = detect_event(
        event, watched=frozenset({"microsoft"}), tranco=frozenset({"alegra.com"})
    )
    assert [d for d, _ in detections] == ["microsoft.secure-a-b-c-d.com"]
