"""Referential family (R-01..R-04): match a domain against watched brands."""

import re

from vigil.detect.data import thresholds
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.levenshtein import bounded_levenshtein
from vigil.detect.techniques.names import DomainName
from vigil.models import Reason

_SPLIT = re.compile(r"[.-]+")


def _tokenize(text: str) -> tuple[str, ...]:
    """Split on dots and hyphens into non-empty lowercase tokens."""
    return tuple(t for t in _SPLIT.split(text) if t)


def _registrable_core(name: DomainName) -> str:
    """Registrable domain with its public suffix stripped."""
    if name.suffix and name.registrable.endswith(f".{name.suffix}"):
        return name.registrable[: -(len(name.suffix) + 1)]
    return name.registrable


def brand_outside_registrable(name: DomainName, watched: frozenset[str] = frozenset()) -> bool:
    """R-01: a watched brand sits in the subdomain but not in the registrable core."""
    if not name.subdomain:
        return False
    subdomain_tokens = set(_tokenize(name.subdomain))
    core_tokens = set(_tokenize(_registrable_core(name)))
    return any(brand in subdomain_tokens and brand not in core_tokens for brand in watched)


def brand_followed_by_tld_token(
    name: DomainName,
    watched: frozenset[str] = frozenset(),
    tld_tokens: frozenset[str] = thresholds.TLD_LIKE_TOKENS,
) -> bool:
    """R-02: a watched brand immediately followed by a TLD-like token in the registrable core."""
    tokens = _tokenize(_registrable_core(name))
    return any(
        tokens[i] in watched and tokens[i + 1] in tld_tokens for i in range(len(tokens) - 1)
    )


def brand_typo_distance(
    name: DomainName,
    watched: frozenset[str] = frozenset(),
    max_distance: int = thresholds.LEVENSHTEIN_MAX_DISTANCE,
) -> bool:
    """R-03: registrable core within edit distance of a watched brand, excluding exact matches."""
    core = _registrable_core(name)
    if core in watched:
        return False
    for brand in watched:
        if abs(len(core) - len(brand)) > max_distance:
            continue
        distance = bounded_levenshtein(core, brand, max_distance)
        if distance:
            return True
    return False


def brand_adjacent_to_auth_term(
    name: DomainName,
    watched: frozenset[str] = frozenset(),
    auth_terms: frozenset[str] = frozenset(),
) -> bool:
    """R-04: a watched brand immediately adjacent to an auth term in the registrable core."""
    tokens = _tokenize(_registrable_core(name))
    return any(
        (tokens[i] in watched and tokens[i + 1] in auth_terms)
        or (tokens[i] in auth_terms and tokens[i + 1] in watched)
        for i in range(len(tokens) - 1)
    )


# evaluation order = decreasing specificity (docs/detections_rules.md)
REFERENTIAL_RULES: tuple[Rule, ...] = (Rule.R_01, Rule.R_02, Rule.R_03, Rule.R_04)


def evaluate_referential(
    name: DomainName,
    watched: frozenset[str] = frozenset(),
    terms: dict[Rule, frozenset[str]] | None = None,
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled referential rule as a Reason, or None."""
    auth_terms = (terms or {}).get(Rule.R_04, frozenset())
    predicates = {
        Rule.R_01: lambda: brand_outside_registrable(name, watched),
        Rule.R_02: lambda: brand_followed_by_tld_token(name, watched),
        Rule.R_03: lambda: brand_typo_distance(name, watched),
        Rule.R_04: lambda: brand_adjacent_to_auth_term(name, watched, auth_terms),
    }
    for rule in REFERENTIAL_RULES:
        if rules is not None and rule not in rules:
            continue
        if predicates[rule]():
            return Reason(family=Family.REFERENTIAL, rule=rule, points=0)
    return None
