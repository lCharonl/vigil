# Scoring

Each rule awards points. A domain's score is the sum of the points of the rules it
matched. A domain is reported only when `score >= score_threshold`.

- Points per rule: `data/rules.yml` (`R-03: {enabled: true, points: 50}`).
- Threshold: `score_threshold` in `data/config.yml`, overridden by `--score-threshold`.
  The default when unset is `0` (every detection is reported).
- Each family contributes at most one rule (the first that matches, in the family's
  rule order), so a family counts once in the sum.
- The score is written as `"score"` in each JSONL detection record.

## Default points

| Rule | Points | Rule | Points |
|---|---|---|---|
| R-01 brand in subdomain | 50 | L-01 MFA terms | 25 |
| R-02 brand + TLD-like token | 50 | L-02 document terms | 20 |
| R-03 Levenshtein typo | 50 | L-03 `www` as component | 20 |
| R-04 brand + auth term | 50 | L-04 generic terms | 10 |
| E-01 mixed scripts | 50 | M-01..M-04 | 5 each |
| E-02 punycode | 30 | | |

With `score_threshold: 50`:

- One referential rule, or E-01, is enough on its own.
- E-02 (punycode) alone is not reported. It needs a second signal.
- Lexical rules need a second signal.
- Morphological rules can never pass alone. This replaces the former
  "morphological only when reinforced" rule.
