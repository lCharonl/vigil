"""Referential family (R-01..R-04): match a domain against watched brands. Stub."""

from vigil.detect.registry import Rule
from vigil.detect.techniques.names import DomainName
from vigil.models import Reason


def evaluate_referential(
    name: DomainName,
    watched: frozenset[str] = frozenset(),
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled referential rule as a Reason, or None."""
    raise NotImplementedError
