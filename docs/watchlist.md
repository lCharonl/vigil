# Watchlist

`data/watchlist.yml` is the list of brands Vigil monitors for impersonation
(typosquatting, homoglyphs, bitsquatting) in Certificate Transparency logs. It
targets the **banking, health, insurance and IT services** sectors, for the
**Europe and United States** regions, and is capped at **10,000 brands**.

## Two tiers

- **`core`** — hand-curated, sourced core in
  [`data/brands_core.seed.yml`](../data/brands_core.seed.yml). These are the brands
  most impersonated according to public threat-intel reports:
  - Check Point *Brand Phishing Report* (Q1/Q2 2026) — Microsoft, Apple, Google,
    Amazon lead; banking and SaaS heavily targeted.
  - APWG *Phishing Activity Trends Report* (Q3/Q4 2025) — SaaS/webmail is the most
    attacked sector; Microsoft in ~22% of attempts.
  - Cofense — cross-industry analysis (Microsoft, Adobe most spoofed, including in
    healthcare).
  - CyberAngel / PhishDef — impersonation of banks, fintech and insurers (PayPal,
    Venmo, Bank of America, UnitedHealthcare, USAA).
  - JCB reported as the most impersonated finance brand by volume.

- **`extended`** — coverage generated from the **Tranco** top-1M list, filtered by
  sector (multilingual token dictionary) and region (EU ccTLDs, `.us`, generic
  gTLDs; non-EU/US ccTLDs are dropped). Tranco rank is a proxy for target value.

## Regenerate

```bash
python scripts/build_watchlist.py
```

The script downloads (and caches under `data/state/`, gitignored) the latest Tranco
list, merges it with the core, deduplicates by registrable domain, caps the total at
10,000 and rewrites `data/watchlist.yml`. No external dependency (standard library +
PyYAML, already required).

## Limits

- **`extended` is not threat-intel.** Token classification on the domain name is a
  heuristic: "popular in a sector" is not "actually impersonated". The high-fidelity
  signal is the `core` tier.
- **False-positive cost.** Once `vigil.detect` is implemented, every brand widens the
  generated permutation space. A watchlist near 10,000 brands sharply increases the
  candidate volume and thus the false-positive risk. The `tier` field lets detection
  weight entries, or restrict to `core`.
- **Imperfect regions.** The region of an `extended` entry is inferred from the
  ccTLD; a global brand on `.com` is tagged `global`.
- If quality candidates run out before the cap, the script stops below 10,000 rather
  than adding noise.
