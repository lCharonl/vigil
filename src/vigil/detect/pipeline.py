"""Detection orchestration: runs the implemented families over a CertEvent."""

from vigil.detect.data.watchlist import is_allowlisted
from vigil.detect.families.encoding import evaluate_encoding
from vigil.detect.families.lexical import evaluate_lexical
from vigil.detect.families.morphological import evaluate_morphological
from vigil.detect.families.referential import evaluate_referential
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.names import DomainName, parse_domain
from vigil.models import CertEvent, Reason

# families with a working evaluator
IMPLEMENTED_FAMILIES: tuple[Family, ...] = (
    Family.MORPHOLOGICAL,
    Family.REFERENTIAL,
    Family.LEXICAL,
    Family.ENCODING,
)


def evaluate_domain(
    name: DomainName,
    digit_exceptions: frozenset[str] = frozenset(),
    watched: frozenset[str] = frozenset(),
    terms: dict[Rule, frozenset[str]] | None = None,
    points: dict[Rule, int] | None = None,
) -> list[Reason]:
    """Collect reasons from the rules in `points` (every rule at 0 points by default).

    Each family contributes at most one reason, carrying the points of its rule.
    """
    rules = frozenset(points) if points is not None else None
    found = (
        evaluate_referential(name, watched, terms, rules),
        evaluate_lexical(name, terms, rules),
        evaluate_encoding(name, rules),
        evaluate_morphological(name, digit_exceptions, rules),
    )
    return [
        reason.model_copy(update={"points": points[Rule(reason.rule)] if points else 0})
        for reason in found
        if reason is not None
    ]


def detect_event(
    cert: CertEvent,
    digit_exceptions: frozenset[str] = frozenset(),
    watched: frozenset[str] = frozenset(),
    terms: dict[Rule, frozenset[str]] | None = None,
    points: dict[Rule, int] | None = None,
    allowlist: frozenset[str] = frozenset(),
    score_threshold: int = 0,
    tranco: frozenset[str] = frozenset(),
) -> list[tuple[str, list[Reason]]]:
    """Return (domain, reasons) for each domain whose summed points reach the threshold."""
    detections: list[tuple[str, list[Reason]]] = []
    for domain in cert.domains:
        name = parse_domain(domain)
        if is_allowlisted(name, allowlist) or name.registrable in tranco:
            continue
        reasons = evaluate_domain(name, digit_exceptions, watched, terms, points)
        if reasons and sum(r.points for r in reasons) >= score_threshold:
            detections.append((domain, reasons))
    return detections
