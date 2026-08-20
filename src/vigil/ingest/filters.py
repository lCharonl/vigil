"""Optional post-ingestion filters applied to CertEvent streams."""

from vigil.models import CertEvent


def is_wildcard(domain: str) -> bool:
    """Return True if any label of the domain is a wildcard."""
    return "*" in domain.split(".")


def strip_wildcards(event: CertEvent) -> CertEvent | None:
    """Drop wildcard SANs; return None if no domain remains."""
    kept = [d for d in event.domains if not is_wildcard(d)]
    if not kept:
        return None
    if len(kept) == len(event.domains):
        return event
    return event.model_copy(update={"domains": kept})
