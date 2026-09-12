"""Statistical family (S-01..S-03): entropy and corpus-baseline rules. Stub."""

from vigil.detect.registry import Rule
from vigil.detect.techniques.names import DomainName
from vigil.models import Reason


def evaluate_statistical(
    name: DomainName,
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled statistical rule as a Reason, or None."""
    raise NotImplementedError
