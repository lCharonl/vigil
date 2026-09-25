# Vigil

Vigil watches Certificate Transparency logs in real time. It looks for
domains impersonating a watched brand — typosquatting, homoglyphs,
bitsquatting.

Built for threat-intel and brand-security teams. It only detects and reports.
No takedowns, no active scanning, no page-content analysis — certificate
metadata only.

## Install

Requires Python 3.12+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

```bash
vigil watch --source fixtures --detection
```

Streams live CertStream by default (`--source certstream`). `fixtures`
replays a local JSONL file instead — good for testing.

Results (detections, or raw certs without `--detection`) are written as
JSON Lines, one object per line, flushed immediately. By default they go to
stdout; pass `--output FILE` to append them to a file instead — handy for a
separate script to tail the file live (see `scripts/tail_results.py`).

Useful flags:

- `--detection` — run detection rules, emit only matches.
- `--rules-config data/rules.yml` — enable/disable individual rules.
- `--watchlist data/watchlist.yml` — brands to monitor.
- `--output FILE` — append results as JSONL to FILE instead of stdout.
- `--metrics` — print throughput stats to stderr instead of individual results.

Run `vigil watch --help` for the full list.

## Docker

Runs `vigil watch` in a container, replaying the bundled fixtures by
default (no external certstream server needed) and writing results as
JSONL to a bind-mounted host directory.

```bash
docker compose up --build
```

Results land in `./data/output/results.jsonl` on the host, one JSON
object per line, flushed as soon as it's written. Watch them live,
colorized, from the host:

```bash
python3 scripts/tail_results.py data/output/results.jsonl
```

To point at a real certstream server instead of the bundled fixtures:

```bash
VIGIL_SOURCE=certstream VIGIL_CERTSTREAM_URL=ws://host.docker.internal:8080/ \
    docker compose up --build
```

(`host.docker.internal` reaches a certstream-server-rust instance
running on the host; adjust for your own setup.)

## Detection rules

Rules are grouped into families (referential, lexical, morphological, ...).
See `docs/detections_rules.md` for the full spec — what each rule catches,
why it's ordered the way it is, and its known blind spots.

Toggle rules in `data/rules.yml`, one line per rule id.

## Tests

```bash
pytest
```
