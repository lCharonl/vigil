#!/usr/bin/env python3
"""Prints CertStream throughput KPIs at 1/5/10-minute checkpoints.

Consumes vigil's CertStreamSource directly (same reconnect/idle-timeout
behaviour as `vigil watch`) and reports, at each checkpoint, cumulative
certificate/domain counts and a per-source breakdown.

Usage:
    python3 scripts/certstream_kpis.py [--certstream-url URL] [--top N]
"""

import argparse
import asyncio
import time
from collections import Counter

from vigil.ingest.certstream import CERTSTREAM_URL, CertStreamSource

CHECKPOINTS = {60: "1 min", 300: "5 min", 600: "10 min"}


def format_snapshot(
    label: str,
    elapsed: float,
    certs: int,
    domains_total: int,
    domains_unique: int,
    by_source: Counter[str],
    top: int,
) -> str:
    lines = [f"\n=== {label} (elapsed {elapsed:.0f}s) ==="]
    lines.append(f"certs:   {certs}  ({certs / elapsed:.2f}/s)")
    lines.append(f"domains: {domains_total} total, {domains_unique} unique")
    lines.append(f"by source (top {top}):")
    for name, count in by_source.most_common(top):
        pct = 100 * count / certs if certs else 0
        lines.append(f"  {name:<45} {count:>6}  ({pct:5.1f}%)")
    return "\n".join(lines)


async def run(url: str, top: int) -> None:
    src = CertStreamSource(url=url)
    certs = 0
    domains_total = 0
    unique_domains: set[str] = set()
    by_source: Counter[str] = Counter()

    start = time.monotonic()
    remaining = sorted(CHECKPOINTS)

    async for event in src.stream():
        certs += 1
        domains_total += len(event.domains)
        unique_domains.update(event.domains)
        by_source[event.source] += 1

        elapsed = time.monotonic() - start
        while remaining and elapsed >= remaining[0]:
            checkpoint = remaining.pop(0)
            print(
                format_snapshot(
                    CHECKPOINTS[checkpoint],
                    elapsed,
                    certs,
                    domains_total,
                    len(unique_domains),
                    by_source,
                    top,
                ),
                flush=True,
            )
        if not remaining:
            break


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certstream-url", default=CERTSTREAM_URL, help="websocket URL")
    parser.add_argument("--top", type=int, default=15, help="sources shown per snapshot")
    args = parser.parse_args()

    try:
        asyncio.run(run(args.certstream_url, args.top))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
