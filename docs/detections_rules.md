# Detection rules

The heuristics Vigil uses to decide that a domain may be impersonating a watched
brand, and how they are grouped.

Weighting, score aggregation and suppression are deliberately **out of scope** for
this version of the document. Rules are defined first; how much each is worth
comes later.

This document is the specification. Code in `src/vigil/detect/` implements it and
must not diverge from it. If a rule changes, change this file first.

---

## 1. Scope and granularity

**Every heuristic evaluates a single domain, never a certificate.**

A certificate carries N SANs. Each is evaluated independently, producing a
`DomainVerdict`. A certificate with at least one matching domain yields exactly
one `Finding` containing all its verdicts.

Grouping by certificate is deliberate: "these three domains share a certificate"
is itself intelligence and a pivot for investigation.

### Wildcards

Wildcard SANs (`*.example.com`) are **skipped** in v1 — not silently dropped.
They are counted and listed in `Finding.skipped_domains`, so the blind spot stays
measurable. Morphological rules would produce noise on the raw string.

> Open item: a wildcard certificate on a freshly registered domain is a campaign
> pattern, not a cosmetic detail. Reintroduce as a signal later.

### Name decomposition

Rules do not all apply to the same part of the name. Before any heuristic runs,
each domain is split with the Public Suffix List (`tldextract`):

- **registrable domain** (eTLD+1) — target of typosquatting and brand-token rules
- **full hostname** — target of label-count and brand-outside-eTLD+1 rules

Rule R-01 depends entirely on this distinction.

---

## 2. Families

Heuristics are grouped by **what they need in order to run**, which also dictates
implementation order:

| Family | Requires | Implementable |
|---|---|---|
| Referential | a watchlist | once `watchlist.yml` exists |
| Lexical | a dictionary | once term lists exist |
| Encoding | nothing | immediately |
| Morphological | nothing | immediately |
| Statistical | a corpus baseline | only after traffic is observed |
| Certificate metadata | the cert object | immediately |

Encoding and morphological rules are pure `str → bool` functions. They are
testable with no fixtures, no network and no configuration — start there.

### One rule per family

**Within a family, rules are evaluated in order of decreasing specificity. The
first one that matches wins, and evaluation moves to the next family.**

This exists to prevent double counting. `microsoft-login.xyz` would otherwise
trigger several correlated referential and lexical rules for a single observed
fact — that a brand sits next to an authentication term.

Ordering by specificity matters for the same reason: the reported reason must be
the most informative one ("brand outside the registrable domain"), not the most
generic one ("contains the word login").

---

## 3. Rules

Each rule has a stable identifier. Identifiers are what `Reason.rule` carries, so
findings stay aggregatable across time and across rule revisions.

### Referential — requires a watchlist

Evaluated in this order.

| ID | Rule | Example |
|---|---|---|
| R-01 | Brand present in a subdomain but absent from the registrable domain | `microsoft.login-example.com` |
| R-02 | Brand followed by a TLD-like token inside the label | `paypal-com-login.example` |
| R-03 | Levenshtein distance ≤ 2 from a watched brand | `micros0ft.com`, `arnazon.net` |
| R-04 | Brand adjacent to an authentication term | `paypal-login.net` |

R-01 is first because nothing about it is accidental: the victim reads the brand
at the start of the hostname while the actual registrable domain is
attacker-controlled.

R-03 covers the classic substitution set — `o→0`, `l→1`, `i→l`, `m→rn`, character
deletion, insertion, transposition, duplication, hyphen injection.

> Known gap: generic combosquatting (`microsoft-support.com` — brand plus a
> neutral affix, no auth vocabulary) matches no referential rule. Such a domain is
> caught lexically or not at all. Accepted for now.

### Lexical — requires a dictionary

| ID | Rule | Terms |
|---|---|---|
| L-01 | MFA / strong-authentication vocabulary | `mfa`, `2fa`, `otp`, `token`, `passkey`, `authenticator`, `sso` |
| L-02 | Document / file-sharing vocabulary | `invoice`, `esign`, `signature`, `contract`, `voicemail`, `shared`, `pdf` |
| L-03 | `www` used as a domain component rather than a subdomain | `www-paypal-login.com` |
| L-04 | Generic auth, finance or urgency vocabulary | `login`, `verify`, `secure`, `billing`, `refund`, `suspended`, `expired` |

L-01 precedes L-04 because MFA vocabulary is far rarer in legitimate traffic and
maps directly to current credential-phishing campaigns, whereas `secure` and
`account` appear in vast numbers of benign domains.

### Encoding — no external resource

| ID | Rule | Example |
|---|---|---|
| E-01 | Characters from more than one Unicode script in a single label | Latin + Cyrillic |
| E-02 | Punycode-encoded label (`xn--`) | `xn--pypal-4ve.com` |

E-01 precedes E-02 because mixed scripts are the attack itself; punycode is only
its transport, and most punycode is legitimate non-Latin registration.

`аpple.com` with a Cyrillic а is visually indistinguishable from the real thing.
A visible typo like `appple.com` at least gives the victim a chance — which is why
these two live in different families and are never conflated.

### Morphological — no external resource

| ID | Rule | Example |
|---|---|---|
| M-01 | Three or more hyphens | `secure-microsoft-login-account.com` |
| M-02 | Registrable domain longer than 40 characters | `microsoft-account-security-verification-center.com` |
| M-03 | Four or more labels in the hostname | `login.microsoft.secure.foo.com` |
| M-04 | Three or more consecutive digits | `office365-auth-92834.net` |

Every rule here is weak alone. They exist to reinforce domains that already
matched elsewhere. One hyphen is unremarkable. `365` is legitimate Microsoft
branding — M-04 must not fire on it.

### Statistical — requires a corpus baseline

Not implementable until enough traffic has been observed. These rules are stubs
that never match until a baseline exists.

| ID | Rule | Example |
|---|---|---|
| S-01 | Readable word combined with a random-looking string | `paypal-x8k2za.com` |
| S-02 | High Shannon entropy across the label | `xj3kq9azp.com` |
| S-03 | TLD statistically over-represented in observed abuse | computed, never a static list |

S-01 precedes S-02 because pure randomness is dominated by CDN and cloud
infrastructure, while word-plus-noise is characteristic of generated phishing
infrastructure.

S-03 is derived from Vigil's own observations. A hardcoded "bad TLD" list ages
badly and encodes someone else's threat model.

### Certificate metadata

| ID | Rule | Example |
|---|---|---|
| C-01 | SAN count above the shared-hosting threshold | 200-domain certificate |

Present for context rather than detection. CDNs and shared hosts trigger it
constantly.

---

## 4. Never sufficient alone

None of the following justifies a finding by itself. All are far too common in
legitimate traffic:

`.xyz` and other cheap TLDs · Let's Encrypt as issuer · recently issued
certificate · punycode · many subdomains · long domain · Cloudflare in the chain

The intended shape is: several weak signals → combined score → DNS/WHOIS/HTTP
enrichment → classification.

---