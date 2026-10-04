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


def test_detect_event_default_reports_every_matching_rule():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    _domain, reasons = detect_event(event, watched=frozenset({"microsoft"}))[0]
    assert {r.rule for r in reasons} == {Rule.R_01, Rule.M_01}


def test_detect_event_combination_needs_every_rule():
    event = make_event(["secure-a-b-c-d.com"])  # M-01 only
    combo = [frozenset({Rule.R_01, Rule.M_01})]
    assert detect_event(event, watched=frozenset({"microsoft"}), detections=combo) == []


def test_detect_event_combination_satisfied_returns_its_rules():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    combo = [frozenset({Rule.R_01, Rule.M_01})]
    detections = detect_event(event, watched=frozenset({"microsoft"}), detections=combo)
    assert [(d, {r.rule for r in rs}) for d, rs in detections] == [
        ("microsoft.secure-a-b-c-d.com", {Rule.R_01, Rule.M_01})
    ]


def test_detect_event_combinations_are_ored():
    event = make_event(["secure-a-b-c-d.com"])
    combos = [frozenset({Rule.R_01, Rule.M_01}), frozenset({Rule.M_01})]
    assert len(detect_event(event, detections=combos)) == 1


def test_detect_event_same_family_combination():
    # M-01 and M-03 both match; first-match-per-family used to hide M-03
    event = make_event(["a-b-c-d.e.f.com"])
    combo = [frozenset({Rule.M_01, Rule.M_03})]
    assert len(detect_event(event, detections=combo)) == 1


def test_detect_event_only_listed_rules_are_reported():
    event = make_event(["microsoft.secure-a-b-c-d.com"])
    detections = detect_event(
        event, watched=frozenset({"microsoft"}), detections=[frozenset({Rule.M_01})]
    )
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
