"""Lexical family (L-01..L-04): match a domain against term dictionaries. Stub."""

from vigil.detect.registry import Rule
from vigil.detect.techniques.names import DomainName
from vigil.models import Reason


def evaluate_lexical(
    name: DomainName,
    terms: dict[Rule, frozenset[str]] | None = None,
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled lexical rule as a Reason, or None."""
    raise NotImplementedError
