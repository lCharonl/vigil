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
- `--rules-config data/rules.yml` — detection rules (rule combinations to report).
- `--watchlist data/watchlist.yml` — brands to monitor.
- `--output FILE` — append results as JSONL to FILE instead of stdout.
- `--metrics` — print throughput stats to stderr instead of individual results.

Run `vigil watch --help` for the full list.

## Docker

Runs `vigil watch` in a container, writing results as JSONL to a
bind-mounted host directory.

```bash
docker compose up --build
```

By default this connects to a certstream-server-rust instance running on
the host, at `ws://host.docker.internal:8080/` (`extra_hosts` in
`docker-compose.yml` makes `host.docker.internal` resolve on native Linux
Docker too, not just Docker Desktop). Start your certstream-server-rust
instance on the host first, then bring the container up.

Results land in `./data/output/results.jsonl` on the host, one JSON
object per line, flushed as soon as it's written. Watch them live,
colorized, from the host:

```bash
python3 scripts/tail_results.py data/output/results.jsonl
```

No certstream server handy? Replay the bundled fixtures instead (no
network dependency):

```bash
VIGIL_SOURCE=fixtures docker compose up --build
```

Or point at a certstream server elsewhere:

```bash
VIGIL_CERTSTREAM_URL=ws://some-other-host:8080/ docker compose up --build
```

## Detection rules

Rules are grouped into families (referential, lexical, morphological, ...).
See `docs/detections_rules.md` for the full spec — what each rule catches,
why it's ordered the way it is, and its known blind spots.

Define detections in `data/rules.yml`, one rule combination per line (e.g. `- [R-03, M-01]`).

## Tests

```bash
pytest
```
