"""Detection orchestration: runs the implemented families over a CertEvent."""

from vigil.detect.morphological import evaluate_morphological
from vigil.detect.names import DomainName, parse_domain
from vigil.detect.rules import Family, Rule
from vigil.models import CertEvent, Reason

# families with a working evaluator
IMPLEMENTED_FAMILIES: tuple[Family, ...] = (Family.MORPHOLOGICAL,)


def evaluate_domain(
    name: DomainName,
    digit_exceptions: frozenset[str] = frozenset(),
    rules: frozenset[Rule] | None = None,
) -> list[Reason]:
    """Collect reasons from the enabled rules (all implemented ones by default)."""
    reasons: list[Reason] = []
    morphological = evaluate_morphological(name, digit_exceptions, rules)
    if morphological is not None:
        reasons.append(morphological)
    return reasons


def detect_event(
    cert: CertEvent,
    digit_exceptions: frozenset[str] = frozenset(),
    rules: frozenset[Rule] | None = None,
) -> list[tuple[str, list[Reason]]]:
    """Return (domain, reasons) for each domain of the cert that matched."""
    detections: list[tuple[str, list[Reason]]] = []
    for domain in cert.domains:
        reasons = evaluate_domain(parse_domain(domain), digit_exceptions, rules)
        if reasons:
            detections.append((domain, reasons))
    return detections
