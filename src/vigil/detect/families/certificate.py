"""Certificate-metadata family (C-01): rules over the cert object itself. Stub."""

from vigil.detect.registry import Rule
from vigil.models import CertEvent, Reason


def evaluate_certificate(
    cert: CertEvent,
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled certificate-metadata rule as a Reason, or None."""
    raise NotImplementedError
