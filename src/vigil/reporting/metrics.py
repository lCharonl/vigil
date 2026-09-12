"""Live throughput and timing metrics for the detection loop."""

import math
import time
from collections import Counter
from dataclasses import dataclass, field

from vigil.models import Reason


def _fmt_duration(seconds: float) -> str:
    """Scale a duration to us/ms/s."""
    if seconds < 1e-3:
        return f"{seconds * 1e6:.0f}us"
    if seconds < 1.0:
        return f"{seconds * 1e3:.1f}ms"
    return f"{seconds:.2f}s"


def _per_second(count: float, span: float) -> float:
    """Rate per second, 0 when the span is empty."""
    return count / span if span > 0 else 0.0


@dataclass
class DetectionMetrics:
    """Accumulates detection-loop throughput and timing counters."""

    start: float = field(default_factory=time.monotonic)
    certs: int = 0
    domains: int = 0
    detections: int = 0
    analysis_seconds: float = 0.0  # summed detect_event() wall time
    per_cert_min: float = math.inf
    per_cert_max: float = 0.0
    by_rule: Counter[str] = field(default_factory=Counter)
    # rolling marks for the last-interval rate
    _mark_time: float = field(default_factory=time.monotonic)
    _mark_domains: int = 0

    def record(
        self,
        n_domains: int,
        elapsed: float,
        detections: list[tuple[str, list[Reason]]],
    ) -> None:
        """Add one processed cert: domain count, detect time, matched rules."""
        self.certs += 1
        self.domains += n_domains
        self.analysis_seconds += elapsed
        if n_domains:
            self.per_cert_min = min(self.per_cert_min, elapsed)
            self.per_cert_max = max(self.per_cert_max, elapsed)
        for _domain, reasons in detections:
            for reason in reasons:
                self.by_rule[reason.rule] += 1
                self.detections += 1

    def snapshot(self, now: float | None = None) -> str:
        """Render a metrics block and advance the rolling interval marks."""
        now = time.monotonic() if now is None else now
        elapsed = now - self.start
        window = now - self._mark_time
        window_domains = self.domains - self._mark_domains

        certs_s = _per_second(self.certs, elapsed)
        domains_s = _per_second(self.domains, elapsed)
        avg = self.analysis_seconds / self.domains if self.domains else 0.0
        cert_min = 0.0 if math.isinf(self.per_cert_min) else self.per_cert_min
        det_rate = 100 * self.detections / self.domains if self.domains else 0.0

        lines = [f"=== detection metrics · elapsed {elapsed:.0f}s ==="]
        lines.append(f"certs:       {self.certs}   ({certs_s:.1f}/s, {60 * certs_s:.0f}/min)")
        lines.append(f"domains:     {self.domains}   ({domains_s:.1f}/s, {60 * domains_s:.0f}/min)")
        lines.append(
            f"  last {window:.0f}s:  {window_domains} domains   "
            f"({_per_second(window_domains, window):.1f}/s)"
        )
        lines.append(
            f"analysis/domain: avg {_fmt_duration(avg)}    "
            f"per-cert {_fmt_duration(cert_min)} min / {_fmt_duration(self.per_cert_max)} max"
        )
        lines.append(
            f"detections:  {self.detections}   "
            f"({60 * _per_second(self.detections, elapsed):.1f}/min, {det_rate:.2f}% of domains)"
        )
        lines.append("by rule:")
        for rule, count in self.by_rule.most_common():
            pct = 100 * count / self.detections if self.detections else 0.0
            lines.append(f"  {rule:<8} {count:>7}   ({pct:5.1f}%)")

        self._mark_time = now
        self._mark_domains = self.domains
        return "\n".join(lines)
