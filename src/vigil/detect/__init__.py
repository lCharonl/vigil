"""Detection layer: evaluates CertEvent domains against the watchlist.

Layout:
- `pipeline` orchestrates the enabled families over a CertEvent
- `registry` holds the Rule/Family catalogue
- `families/` has one module per family (referential, lexical, encoding, morphological)
- `techniques/` has pure string helpers (names, levenshtein, permutations, homoglyphs)
- `data/` holds the watchlist, lexical terms, rule toggles and numeric thresholds
"""
