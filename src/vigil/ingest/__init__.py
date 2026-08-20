"""Ingestion layer: turns raw certificate feeds into CertEvent objects.

Deliberately decoupled from detection so it can be swapped out (e.g. rewritten in
Rust later) without touching anything under vigil.detect. See docs/architecture.md.
"""
