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

Useful flags:

- `--detection` — run detection rules, print only matches.
- `--rules-config data/rules.yml` — enable/disable individual rules.
- `--watchlist data/watchlist.yml` — brands to monitor.
- `--metrics` — print throughput stats instead of individual detections.

Run `vigil watch --help` for the full list.

## Detection rules

Rules are grouped into families (referential, lexical, morphological, ...).
See `docs/detections_rules.md` for the full spec — what each rule catches,
why it's ordered the way it is, and its known blind spots.

Toggle rules in `data/rules.yml`, one line per rule id.

## Tests

```bash
pytest
```
