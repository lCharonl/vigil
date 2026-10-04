# Rule combinations

A domain is reported when it matches every rule of at least one combination listed
under `detections` in `data/rules.yml`.

```yaml
detections:
  - [R-04]          # one rule is enough
  - [R-03, M-01]    # both rules must match
```

- Inside a combination the rules are ANDed; combinations are ORed.
- Only rules that appear in a combination are evaluated.
- All matching rules count, including several from the same family (e.g. M-01 and M-03).
- Rule ids are case-insensitive; unknown ids or empty combinations are rejected at startup.
- If the file is missing, every rule alone is a detection.
- Override the file with `--rules-config`.
- Each JSONL record lists the rules of the satisfied combinations in `"rules"`.
- Ranked domains (`tranco_csv`) and allowlisted domains are never reported.
