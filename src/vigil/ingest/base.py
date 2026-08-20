"""Common ingestion contract shared by every certificate stream source."""

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from vigil.models import CertEvent


@runtime_checkable
class Source(Protocol):
    """A source of certificate events.

    Ingestion is deliberately decoupled from detection: a `Source` only knows how to
    produce `CertEvent` objects, and has no notion of watchlists, scoring, or
    findings. This lets the ingestion layer be rewritten (e.g. in Rust) without
    touching detection.
    """

    async def stream(self) -> AsyncIterator[CertEvent]:
        """Yield CertEvent objects indefinitely, or until the underlying feed ends."""
        ...
