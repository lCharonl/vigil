"""Detection orchestration: runs the implemented families over a CertEvent."""

from vigil.detect.data.watchlist import is_allowlisted
from vigil.detect.families.morphological import evaluate_morphological
from vigil.detect.families.referential import evaluate_referential
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.names import DomainName, parse_domain
from vigil.models import CertEvent, Reason

# families with a working evaluator
IMPLEMENTED_FAMILIES: tuple[Family, ...] = (Family.MORPHOLOGICAL, Family.REFERENTIAL)


def evaluate_domain(
    name: DomainName,
    digit_exceptions: frozenset[str] = frozenset(),
    watched: frozenset[str] = frozenset(),
    terms: dict[Rule, frozenset[str]] | None = None,
    rules: frozenset[Rule] | None = None,
) -> list[Reason]:
    """Collect reasons from the enabled rules (all implemented ones by default).

    Morphological reasons are weak alone (docs/detections_rules.md, "Morphological")
    and are kept only if another family also matched the same domain.
    """
    reasons: list[Reason] = []
    morphological = evaluate_morphological(name, digit_exceptions, rules)
    referential = evaluate_referential(name, watched, terms, rules)
    if referential is not None:
        reasons.append(referential)
    if morphological is not None and reasons:
        reasons.append(morphological)
    return reasons


def detect_event(
    cert: CertEvent,
    digit_exceptions: frozenset[str] = frozenset(),
    watched: frozenset[str] = frozenset(),
    terms: dict[Rule, frozenset[str]] | None = None,
    rules: frozenset[Rule] | None = None,
    allowlist: frozenset[str] = frozenset(),
) -> list[tuple[str, list[Reason]]]:
    """Return (domain, reasons) for each domain of the cert that matched."""
    detections: list[tuple[str, list[Reason]]] = []
    for domain in cert.domains:
        name = parse_domain(domain)
        if is_allowlisted(name, allowlist):
            continue
        reasons = evaluate_domain(name, digit_exceptions, watched, terms, rules)
        if reasons:
            detections.append((domain, reasons))
    return detections
