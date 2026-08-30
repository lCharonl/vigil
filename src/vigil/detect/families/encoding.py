"""Encoding family (E-01..E-02): mixed-script and punycode labels. Stub."""

from vigil.detect.registry import Rule
from vigil.detect.techniques.names import DomainName
from vigil.models import Reason


def evaluate_encoding(
    name: DomainName,
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled encoding rule as a Reason, or None."""
    raise NotImplementedError
