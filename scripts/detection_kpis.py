#!/usr/bin/env python3
"""Prints detection throughput, timing and per-rule counts over a 5-minute window.

Consumes vigil's CertStreamSource (same reconnect/idle-timeout behaviour as
`vigil watch`), runs the detection pipeline on every non-wildcard domain, and
prints a DetectionMetrics snapshot at the end of the window.

Usage:
    python3 scripts/detection_kpis.py [--certstream-url URL] [--duration SECONDS]
"""

import argparse
import asyncio
import time

from vigil.detect.data.watchlist import load_legitimate_domains
from vigil.detect.families.morphological import numeric_exceptions
from vigil.detect.pipeline import detect_event
from vigil.ingest.certstream import CERTSTREAM_URL, CertStreamSource
from vigil.ingest.filters import strip_wildcards
from vigil.reporting.metrics import DetectionMetrics

DEFAULT_DURATION = 300


async def run(url: str, duration: float, watchlist: str) -> None:
    src = CertStreamSource(url=url)
    digit_exceptions = numeric_exceptions(load_legitimate_domains(watchlist))
    stats = DetectionMetrics()

    start = time.monotonic()
    async for event in src.stream():
        event = strip_wildcards(event)
        if event is None:
            continue
        t0 = time.perf_counter()
        results = detect_event(event, digit_exceptions)
        stats.record(len(event.domains), time.perf_counter() - t0, results)

        if time.monotonic() - start >= duration:
            print(stats.snapshot(), flush=True)
            break


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certstream-url", default=CERTSTREAM_URL, help="websocket URL")
    parser.add_argument(
        "--duration", type=float, default=DEFAULT_DURATION, help="window in seconds"
    )
    parser.add_argument(
        "--watchlist", default="data/watchlist.yml", help="watchlist for M-04 exceptions"
    )
    args = parser.parse_args()

    try:
        asyncio.run(run(args.certstream_url, args.duration, args.watchlist))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
