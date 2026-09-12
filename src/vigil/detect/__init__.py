"""Detection layer: scores CertEvent domains against the watchlist.

Layout:
- `pipeline` orchestrates the enabled families over a CertEvent
- `registry` holds the Rule/Family catalogue; `scoring` builds the Finding (stub)
- `families/` has one module per family (morphological implemented, rest stubs)
- `techniques/` has pure string helpers: `names` (PSL split), plus `permutations`
  and `homoglyphs` (both stubs)
- `data/` holds the watchlist, lexical terms and numeric thresholds
"""
