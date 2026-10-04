"""Detection layer: matches CertEvent domains against detection rules.

Layout:
- `pipeline` orchestrates the enabled families over a CertEvent
- `registry` holds the Rule/Family catalogue
- `families/` has one module per family (morphological, referential implemented, rest stubs)
- `techniques/` has pure string helpers: `names` (PSL split), plus `permutations`
  and `homoglyphs` (both stubs)
- `data/` holds the watchlist, lexical terms and numeric thresholds
"""
