"""Lexical family (L-01..L-04): match a domain against term dictionaries."""

import re

from vigil.detect.registry import Family, Rule
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


def mfa_term_present(name: DomainName, terms: frozenset[str] = frozenset()) -> bool:
    """L-01: MFA / strong-authentication vocabulary anywhere in the hostname."""
    return any(token in terms for token in _tokenize(name.fqdn))


def document_term_present(name: DomainName, terms: frozenset[str] = frozenset()) -> bool:
    """L-02: document / file-sharing vocabulary anywhere in the hostname."""
    return any(token in terms for token in _tokenize(name.fqdn))


def www_as_domain_component(name: DomainName) -> bool:
    """L-03: `www` used as a domain component rather than as the real subdomain."""
    if name.subdomain == "www":
        return False
    return "www" in _tokenize(_registrable_core(name))


def generic_term_present(name: DomainName, terms: frozenset[str] = frozenset()) -> bool:
    """L-04: generic auth, finance or urgency vocabulary anywhere in the hostname."""
    return any(token in terms for token in _tokenize(name.fqdn))


LEXICAL_RULES: tuple[Rule, ...] = (Rule.L_01, Rule.L_02, Rule.L_03, Rule.L_04)


def evaluate_lexical(
    name: DomainName,
    terms: dict[Rule, frozenset[str]] | None = None,
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled lexical rule as a Reason, or None."""
    mfa_terms = (terms or {}).get(Rule.L_01, frozenset())
    document_terms = (terms or {}).get(Rule.L_02, frozenset())
    generic_terms = (terms or {}).get(Rule.L_04, frozenset())
    predicates = {
        Rule.L_01: lambda: mfa_term_present(name, mfa_terms),
        Rule.L_02: lambda: document_term_present(name, document_terms),
        Rule.L_03: lambda: www_as_domain_component(name),
        Rule.L_04: lambda: generic_term_present(name, generic_terms),
    }
    for rule in LEXICAL_RULES:
        if rules is not None and rule not in rules:
            continue
        if predicates[rule]():
            return Reason(family=Family.LEXICAL, rule=rule, points=0)
    return None
