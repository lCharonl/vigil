"""CertStream websocket source: streams CertEvent objects from a certstream server.

The public certstream.calidog.io instance is defunct (it accepts connections but
no longer pushes any messages), so the default here points at a self-hosted
https://github.com/reloading01/certstream-server-rust instance instead. Run one
locally (see certstream-server-rust/README.md) or point --certstream-url at
whichever instance you have.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import websockets

from vigil.models import CertEvent

logger = logging.getLogger(__name__)

CERTSTREAM_URL = "ws://127.0.0.1:8080/"
INITIAL_BACKOFF_SECONDS = 1
MAX_BACKOFF_SECONDS = 60
IDLE_TIMEOUT_SECONDS = 45


def parse_certstream_message(message: dict[str, Any]) -> CertEvent | None:
    if message.get("message_type") != "certificate_update":
        return None

    data = message["data"]
    leaf_cert = data["leaf_cert"]
    issuer = leaf_cert.get("issuer") or {}

    return CertEvent(
        serial_number=leaf_cert["serial_number"],
        signature_algo=leaf_cert["signature_algorithm"],
        issuer_country=issuer.get("C") or None,
        issuer_organisation=issuer.get("O") or None,
        issuer_common_name=issuer.get("CN") or "",
        validity_not_before=datetime.fromtimestamp(leaf_cert["not_before"], tz=UTC),
        validity_not_after=datetime.fromtimestamp(leaf_cert["not_after"], tz=UTC),
        domains=leaf_cert["all_domains"],
        source=(data.get("source") or {}).get("name", "unknown"),
        cert_index=data.get("cert_index"),
        is_precert=data.get("update_type") == "PrecertLogEntry",
    )


class _IdleTimeout(Exception):
    """Raised when the connection stays open but stops delivering messages."""


class CertStreamSource:
    def __init__(
        self,
        url: str = CERTSTREAM_URL,
        idle_timeout: float = IDLE_TIMEOUT_SECONDS,
    ) -> None:
        self.url = url
        self.idle_timeout = idle_timeout

    async def stream(self) -> AsyncIterator[CertEvent]:
        backoff = INITIAL_BACKOFF_SECONDS
        while True:
            try:
                async with websockets.connect(self.url) as ws:
                    logger.info("connected to %s", self.url)
                    backoff = INITIAL_BACKOFF_SECONDS
                    while True:
                        try:
                            raw = await asyncio.wait_for(ws.recv(), timeout=self.idle_timeout)
                        except TimeoutError as exc:
                            raise _IdleTimeout(
                                f"no messages in {self.idle_timeout:.0f}s"
                            ) from exc
                        try:
                            message = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning("dropping non-JSON message from %s", self.url)
                            continue
                        event = parse_certstream_message(message)
                        if event is not None:
                            yield event
            except (websockets.exceptions.WebSocketException, OSError, _IdleTimeout) as exc:
                logger.warning(
                    "connection to %s lost (%s), reconnecting in %ds", self.url, exc, backoff
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
