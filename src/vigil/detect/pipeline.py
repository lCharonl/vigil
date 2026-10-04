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
    rules: frozenset[Rule] | None = None,
) -> list[Reason]:
    """Collect a reason for every matching rule in `rules` (all rules by default)."""
    return [
        *evaluate_referential(name, watched, terms, rules),
        *evaluate_lexical(name, terms, rules),
        *evaluate_encoding(name, rules),
        *evaluate_morphological(name, digit_exceptions, rules),
    ]


def detect_event(
    cert: CertEvent,
    digit_exceptions: frozenset[str] = frozenset(),
    watched: frozenset[str] = frozenset(),
    terms: dict[Rule, frozenset[str]] | None = None,
    detections: list[frozenset[Rule]] | None = None,
    allowlist: frozenset[str] = frozenset(),
    tranco: frozenset[str] = frozenset(),
) -> list[tuple[str, list[Reason]]]:
    """Return (domain, reasons) for each domain that satisfies a rule combination."""
    if detections is None:
        detections = [frozenset({rule}) for rule in Rule]
    rules = frozenset().union(*detections)
    results: list[tuple[str, list[Reason]]] = []
    for domain in cert.domains:
        name = parse_domain(domain)
        if is_allowlisted(name, allowlist) or name.registrable in tranco:
            continue
        reasons = evaluate_domain(name, digit_exceptions, watched, terms, rules)
        matched = frozenset(Rule(r.rule) for r in reasons)
        hit = frozenset().union(*(combo for combo in detections if combo <= matched))
        if hit:
            results.append((domain, [r for r in reasons if Rule(r.rule) in hit]))
    return results
