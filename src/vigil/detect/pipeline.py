"""Detection orchestration: runs the implemented families over a CertEvent."""

from vigil.detect.morphological import evaluate_morphological
from vigil.detect.names import DomainName, parse_domain
from vigil.models import CertEvent, Reason


def evaluate_domain(
    name: DomainName, digit_exceptions: frozenset[str] = frozenset()
) -> list[Reason]:
    """Collect reasons from every implemented family (morphological for now)."""
    reasons: list[Reason] = []
    morphological = evaluate_morphological(name, digit_exceptions)
    if morphological is not None:
        reasons.append(morphological)
    return reasons


def detect_event(
    cert: CertEvent, digit_exceptions: frozenset[str] = frozenset()
) -> list[tuple[str, list[Reason]]]:
    """Return (domain, reasons) for each domain of the cert that matched."""
    detections: list[tuple[str, list[Reason]]] = []
    for domain in cert.domains:
        reasons = evaluate_domain(parse_domain(domain), digit_exceptions)
        if reasons:
            detections.append((domain, reasons))
    return detections
