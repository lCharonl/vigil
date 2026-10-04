#!/usr/bin/env python3
"""Converts the Tranco top-1M CSV into a lookup file, then filters a results
JSONL to keep only detections whose registrable domain is absent from Tranco.

Usage:
    python3 scripts/filter_tranco.py data/output/results.jsonl
    python3 scripts/filter_tranco.py data/output/results.jsonl --output data/output/results.non_tranco.jsonl

    # live stream: tail a growing results file, e.g. from
    #   vigil watch --detection --output data/output/results.jsonl
    python3 scripts/filter_tranco.py data/output/results.jsonl --follow
"""

import argparse
import csv
import json
from pathlib import Path

from tail_results import POLL_INTERVAL_SECONDS, follow

from vigil.detect.techniques.names import parse_domain

DEFAULT_TRANCO_CSV = Path("data/state/tranco_top1m.csv")
DEFAULT_TRANCO_SET = Path("data/state/tranco_domains.txt")


def build_tranco_set(csv_path: Path, out_path: Path) -> frozenset[str]:
    """Converts the ranked Tranco CSV into a deduped, sorted domain list file."""
    domains: set[str] = set()
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                domains.add(row[1].strip().lower())
    out_path.write_text("\n".join(sorted(domains)) + "\n", encoding="utf-8")
    return frozenset(domains)


def load_tranco_set(csv_path: Path, out_path: Path) -> frozenset[str]:
    """Returns the Tranco domain set, rebuilding the comparison file if missing or stale."""
    if out_path.exists() and out_path.stat().st_mtime >= csv_path.stat().st_mtime:
        return frozenset(out_path.read_text(encoding="utf-8").split())
    return build_tranco_set(csv_path, out_path)


def filter_non_tranco(
    input_path: Path, output_path: Path, tranco: frozenset[str]
) -> tuple[int, int]:
    """Writes records whose registrable domain isn't in Tranco; returns (kept, total)."""
    kept = total = 0
    with input_path.open(encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line in src:
            line = line.strip()
            if not line:
                continue
            total += 1
            record = json.loads(line)
            registrable = parse_domain(record["domain"]).registrable
            if registrable not in tranco:
                dst.write(line + "\n")
                kept += 1
    return kept, total


def follow_non_tranco(
    input_path: Path,
    output_path: Path | None,
    tranco: frozenset[str],
    from_start: bool,
    poll_interval: float,
) -> None:
    """Tails a growing results JSONL, printing (and optionally appending) non-Tranco records."""
    dst = output_path.open("a", encoding="utf-8") if output_path else None
    try:
        for line in follow(input_path, from_start, poll_interval):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            registrable = parse_domain(record["domain"]).registrable
            if registrable not in tranco:
                print(line, flush=True)
                if dst:
                    dst.write(line + "\n")
                    dst.flush()
    finally:
        if dst:
            dst.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="results JSONL to filter (or tail with --follow)")
    parser.add_argument(
        "--output", type=Path, default=None, help="filtered JSONL (default: <input>.non_tranco.jsonl, none in --follow mode)"
    )
    parser.add_argument("--tranco-csv", type=Path, default=DEFAULT_TRANCO_CSV)
    parser.add_argument("--tranco-set", type=Path, default=DEFAULT_TRANCO_SET)
    parser.add_argument(
        "--follow", action="store_true", help="tail the input file live instead of a one-shot pass"
    )
    parser.add_argument(
        "--from-start", action="store_true", help="with --follow, replay the whole file first"
    )
    parser.add_argument("--poll-interval", type=float, default=POLL_INTERVAL_SECONDS)
    args = parser.parse_args()

    tranco = load_tranco_set(args.tranco_csv, args.tranco_set)

    if args.follow:
        try:
            follow_non_tranco(
                args.input, args.output, tranco, args.from_start, args.poll_interval
            )
        except KeyboardInterrupt:
            pass
        return

    output = args.output or args.input.with_name(f"{args.input.stem}.non_tranco{args.input.suffix}")
    kept, total = filter_non_tranco(args.input, output, tranco)
    print(f"{kept}/{total} domains not in Tranco top 1M -> {output}")


if __name__ == "__main__":
    main()
