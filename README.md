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

Settings resolve in this order: CLI flag, then `data/config.yml`, then built-in
defaults. Pass `--config FILE` to use another run config.

Results (detections, or raw certs with `--no-detection`) are written as
JSON Lines, one object per line, flushed immediately. By default they go to
stdout; pass `--output FILE` to append them to a file instead — handy for a
separate script to tail the file live (see `scripts/tail_results.py`). The line
format is described in `docs/architecture.md` ("Output contract").

Useful flags:

- `--config FILE` — run config YAML (default `data/config.yml`).
- `--source certstream|fixtures` — feed to read.
- `--certstream-url URL` — websocket URL for `certstream`.
- `--fixtures-path FILE` — JSONL file replayed by `fixtures`.
- `--detection/--no-detection` — run detection rules and emit only matches, or emit raw certs.
- `--rules-config data/rules.yml` — enable/disable individual rules.
- `--watchlist data/watchlist.yml` — brands to monitor.
- `--skip-wildcards/--no-skip-wildcards` — drop wildcard SANs.
- `--output FILE` — append results as JSONL to FILE instead of stdout.
- `--metrics` — print throughput stats to stderr instead of individual results (needs detection).
- `--metrics-interval SECONDS` — delay between metrics snapshots.

Run `vigil watch --help` for the full list.

## Scripts

- `scripts/tail_results.py` — live, colorized tail of a results JSONL file.
- `scripts/build_watchlist.py` — regenerate `data/watchlist.yml` (see `docs/watchlist.md`).
- `scripts/detection_kpis.py` — detection throughput/timing over a time window.
- `scripts/certstream_kpis.py` — CertStream throughput at 1/5/10-minute checkpoints.

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

The image's own default command (without compose) replays the fixtures. Results land in `./data/output/results.jsonl` on the host, one JSON
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

Toggle rules in `data/rules.yml`, one line per rule id.

## Tests

```bash
pytest
```
