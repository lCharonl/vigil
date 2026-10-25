# Architecture

Vigil is split into layers that only communicate through the models defined in
`vigil.models` (`CertEvent`, and `Finding` once scoring exists):

- **Ingestion** (`vigil.ingest`) turns a certificate feed (CertStream websocket, or a
  recorded JSONL fixture) into an async stream of `CertEvent` objects. Every source
  implements the `Source` protocol (`async def stream(self) -> AsyncIterator[CertEvent]`)
  defined in `vigil.ingest.base`. Ingestion knows nothing about watchlists, brands, or
  scoring — it only maps raw feed messages to `CertEvent`, with no normalisation of
  domain strings (case, wildcards, IDNA, ...). `CertStreamSource` talks to a
  [certstream-server-rust](https://github.com/reloading01/certstream-server-rust)
  instance (the public `certstream.calidog.io` feed is defunct); run one locally
  and pass its URL via `vigil watch --certstream-url`. `ingest/filters.py` holds the
  optional post-ingestion filter that drops wildcard SANs.

- **Detection** (`vigil.detect`) consumes `CertEvent` objects plus the watchlist and
  produces, per matching domain, a list of `Reason` objects. `pipeline.py` runs the
  enabled families over each domain of a cert; `registry.py` is the Rule/Family
  catalogue. One module per family lives in `detect/families/` (`referential`,
  `lexical`, `encoding`, `morphological`, all implemented). Morphological reasons are
  weak alone and are kept only if another family also matched the same domain (unless
  `rules` is scoped to morphological only). `detect/techniques/` holds pure string
  helpers (PSL split, Levenshtein, permutations, homoglyphs). `detect/data/` holds the
  loaders for the watchlist, lexical terms, shared-hosting suffixes, rule toggles and
  numeric thresholds. Allowlisted domains (watchlist legitimate domains and
  shared-hosting suffixes) are skipped.

- **Reporting** (`vigil.reporting`) renders run-loop observability (throughput, timing,
  per-rule counts) for `vigil watch --metrics`.

- **Output** (`vigil.output`) serializes records to JSON Lines (stdout or an appended
  file), flushed per line.

- **CLI** (`vigil.cli`) wires everything: `commands.py` (typer `watch` command),
  `run_config.py` (loads `data/config.yml`), `stream.py` (the async loop).

This split exists so ingestion can be rewritten in a faster language later (Rust is
planned) without touching detection: as long as the replacement produces the same
`CertEvent` shape, nothing downstream needs to change.

## Data flow

```
Source.stream() -> CertEvent -> [strip_wildcards] -> detect_event -> (domain, reasons) -> JSONLWriter
```

`Finding` and `DomainVerdict` (`vigil.models`) describe the target per-certificate
contract, documented in `schemas/finding.v1.json`. There is no scoring layer yet, so
they are not produced today.

## Configuration

`vigil watch` settings resolve in this order: CLI flag, then `data/config.yml`
(`--config` to change the path), then hardcoded defaults in `RunConfig`. Rule toggles
live in `data/rules.yml`, the brands in `data/watchlist.yml`.

## Output contract

What `vigil watch` actually writes, one JSON object per line.

With `--detection` (one line per matching domain):

| Field | Type | Meaning |
|---|---|---|
| `detected_at` | string (UTC ISO 8601) | time the line was written |
| `source` | string | CT log name |
| `serial_number` | string | certificate serial |
| `domain` | string | the matching SAN |
| `families` | string[] | distinct families that matched |
| `rules` | string[] | rule ids that matched (e.g. `R-01`) |

Without detection (one line per certificate): `detected_at`, `source`,
`serial_number`, and `domains` (string[]) in place of the last three fields.

With `--metrics` (detection only), no result lines are written; snapshots go to stderr.
