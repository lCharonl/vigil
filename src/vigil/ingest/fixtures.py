"""Fixture source: replays a recorded CertStream JSONL file, for offline tests/demos."""

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from vigil.ingest.certstream import parse_certstream_message
from vigil.models import CertEvent

logger = logging.getLogger(__name__)


class FixtureSource:
    """Replays a JSONL file of raw CertStream messages as CertEvent objects.

    Each non-empty line is expected to be a single raw CertStream JSON message
    (the same shape CertStreamSource receives over the websocket), so both sources
    share the same mapping logic in vigil.ingest.certstream.parse_certstream_message.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    async def stream(self) -> AsyncIterator[CertEvent]:
        with self.path.open(encoding="utf-8") as fixture_file:
            for line_number, line in enumerate(fixture_file, start=1):
                line = line.strip()
                if not line:
                    continue
                message = json.loads(line)
                event = parse_certstream_message(message)
                if event is None:
                    logger.debug("skipping non-certificate message on line %d", line_number)
                    continue
                yield event
