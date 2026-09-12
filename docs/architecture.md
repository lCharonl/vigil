# Architecture

Vigil is split into three layers that only communicate through the `CertEvent` and
`Finding` models defined in `vigil.models`:

- **Ingestion** (`vigil.ingest`) turns a certificate feed (CertStream websocket, or a
  recorded JSONL fixture) into an async stream of `CertEvent` objects. Every source
  implements the `Source` protocol (`async def stream(self) -> AsyncIterator[CertEvent]`)
  defined in `vigil.ingest.base`. Ingestion knows nothing about watchlists, brands, or
  scoring — it only maps raw feed messages to `CertEvent`, with no normalisation of
  domain strings (case, wildcards, IDNA, ...). `CertStreamSource` talks to a
  [certstream-server-rust](https://github.com/reloading01/certstream-server-rust)
  instance (the public `certstream.calidog.io` feed is defunct); run one locally
  and pass its URL via `vigil watch --certstream-url`.

- **Detection** (`vigil.detect`) consumes `CertEvent` objects and the watchlist
  (`data/watchlist.yml`) to produce `Finding` objects. `pipeline.py` runs the enabled
  families over each cert; `registry.py` is the Rule/Family catalogue and `scoring.py`
  builds the `Finding` (stub). One module per family lives in `detect/families/` (only
  `morphological.py` is implemented; the rest are stubs). `detect/techniques/` holds
  pure string helpers — `names.py` (PSL split), `permutations.py` and `homoglyphs.py`
  (both stubs) — and `detect/data/` holds the watchlist reader, lexical terms and
  numeric thresholds.

- **Reporting** (`vigil.reporting`) renders run-loop observability (throughput, timing,
  per-rule counts) for `vigil watch --metrics`.

- **Output** (`vigil.output`) serializes `Finding` objects, currently to JSON Lines.

This split exists so ingestion can be rewritten in a faster language later (Rust is
planned, see `docs/adr/0001-python-first.md`) without touching detection: as long as
the replacement produces the same `CertEvent` shape, nothing downstream needs to
change. `schemas/finding.v1.json` documents the `Finding` contract independently of
any language, for consumers that live outside this repository.

## Data flow

```
Source.stream() -> CertEvent -> detect.* -> Finding -> output.JSONLWriter
```

`vigil.cli` wires a `Source` to (eventually) the detection pipeline and an output
writer. Today, with detection stubbed, `vigil watch` only ingests and prints
`CertEvent` objects to stdout.
