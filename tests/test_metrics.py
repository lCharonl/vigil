"""Tests for DetectionMetrics accumulation and snapshot rendering."""

from vigil.detect.metrics import DetectionMetrics, _fmt_duration
from vigil.models import Reason


def _reason(rule: str) -> Reason:
    return Reason(family="morphological", rule=rule, points=0)


def test_record_accumulates():
    m = DetectionMetrics()
    m.record(3, 0.006, [("a-b-c.com", [_reason("M-01")])])
    m.record(2, 0.004, [])
    assert m.certs == 2
    assert m.domains == 5
    assert m.detections == 1
    assert m.by_rule["M-01"] == 1
    assert abs(m.analysis_seconds - 0.010) < 1e-9
    assert m.per_cert_min == 0.004
    assert m.per_cert_max == 0.006


def test_record_counts_multiple_reasons():
    m = DetectionMetrics()
    m.record(1, 0.001, [("x.com", [_reason("M-01"), _reason("M-03")])])
    assert m.detections == 2
    assert m.by_rule["M-03"] == 1


def test_snapshot_contains_sections():
    m = DetectionMetrics()
    m.record(4, 0.002, [("a.b.c.d.com", [_reason("M-03")])])
    out = m.snapshot()
    for token in ("certs:", "domains:", "/s", "analysis/domain", "by rule", "M-03"):
        assert token in out


def test_snapshot_zero_domains_no_crash():
    out = DetectionMetrics().snapshot()
    assert "detection metrics" in out


def test_snapshot_advances_interval_mark():
    m = DetectionMetrics()
    m.record(10, 0.001, [])
    assert "10 domains" in m.snapshot()
    m.record(5, 0.001, [])
    assert "5 domains" in m.snapshot()


def test_fmt_duration_units():
    assert _fmt_duration(0.0000123).endswith("us")
    assert _fmt_duration(0.0123).endswith("ms")
    assert _fmt_duration(2.5).endswith("s")
    assert "ms" not in _fmt_duration(2.5)
