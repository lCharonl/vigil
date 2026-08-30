"""Numeric thresholds and fixed tokens for detection rules."""

# R-03: max Levenshtein distance from a watched brand
LEVENSHTEIN_MAX_DISTANCE: int = 2

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

# L-03: www used as a domain component rather than a subdomain
WWW_COMPONENT_TOKEN: str = "www"

# E-02: punycode label prefix
PUNYCODE_PREFIX: str = "xn--"
