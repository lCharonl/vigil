"""Numeric thresholds and fixed tokens for detection rules."""

# R-03: max Levenshtein distance from a watched brand
LEVENSHTEIN_MAX_DISTANCE: int = 2

# R-03: registrable core length below which typo distance is not evaluated
LEVENSHTEIN_MIN_CORE_LENGTH: int = 3

# M-01: minimum hyphen count
MIN_HYPHENS: int = 3

# M-02: registrable domain length considered too long (chars, exclusive)
MAX_REGISTRABLE_LENGTH: int = 40

# M-03: minimum label count in the hostname
MIN_LABELS: int = 4

# M-04: minimum run of consecutive digits
# note: 365 must not fire; derive the exception from watchlist brand tokens
MIN_CONSECUTIVE_DIGITS: int = 3

# C-01: SAN count above the shared-hosting threshold
SAN_COUNT_THRESHOLD: int = 200

# R-02: short tokens that look like a real TLD when embedded in a label
TLD_LIKE_TOKENS: frozenset[str] = frozenset({
    "com", "net", "org", "info", "biz", "co", "io", "gov", "edu",
})

# L-03: www used as a domain component rather than a subdomain
WWW_COMPONENT_TOKEN: str = "www"

# E-02: punycode label prefix
PUNYCODE_PREFIX: str = "xn--"
