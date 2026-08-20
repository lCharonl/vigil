# ADR 0001: Python for phase 1, ingestion rewritten in Rust later

## Status
Accepted

## Context
Vigil needs to be usable quickly to validate detection heuristics (permutations,
homoglyphs, scoring) against real CertStream traffic. Certificate Transparency logs
produce a high volume of events, and a production ingestion path will eventually need
to be fast and resource-efficient enough to keep up with multiple log feeds
concurrently.

## Decision
Phase 1 is written entirely in Python. Detection logic changes fast during this phase
and benefits from Python's iteration speed; ingestion volume during validation is
modest enough that Python's throughput is not the bottleneck yet.

Ingestion and detection are kept strictly decoupled behind the `CertEvent` /
`Finding` models and the `Source` protocol (see `docs/architecture.md`), so that
ingestion can later be rewritten in Rust and exposed to the Python detection layer
(e.g. via a queue, socket, or FFI boundary) without requiring changes to
`vigil.detect` or `vigil.output`.

## Consequences
- Detection code should never depend on `vigil.ingest` internals beyond the
  `CertEvent` model, to keep the boundary real rather than aspirational.
- Ingestion code should avoid Python-specific conveniences that would be awkward to
  replicate in Rust; `schemas/finding.v1.json` is committed as a static,
  language-independent contract for `Finding` rather than generated at runtime only.
- A future ADR should record the actual Rust rewrite decision when it happens.
