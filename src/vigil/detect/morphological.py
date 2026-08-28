"""Morphological rules (M-01..M-04): weak, pure structural predicates."""

import re
from collections.abc import Iterable

from vigil.detect import config
from vigil.detect.names import DomainName
from vigil.detect.rules import Family, Rule
from vigil.models import Reason

_DIGIT_RUN = re.compile(r"\d+")


def has_min_hyphens(name: DomainName, minimum: int = config.MIN_HYPHENS) -> bool:
    """M-01: three or more hyphens in the hostname."""
    return name.fqdn.count("-") >= minimum


def registrable_too_long(name: DomainName, maximum: int = config.MAX_REGISTRABLE_LENGTH) -> bool:
    """M-02: registrable domain longer than the limit."""
    return len(name.registrable) > maximum


def has_min_labels(name: DomainName, minimum: int = config.MIN_LABELS) -> bool:
    """M-03: four or more labels in the hostname."""
    return len(name.labels) >= minimum


def has_digit_run(
    name: DomainName,
    minimum: int = config.MIN_CONSECUTIVE_DIGITS,
    exceptions: frozenset[str] = frozenset(),
) -> bool:
    """M-04: a run of consecutive digits, ignoring known brand tokens."""
    return any(
        len(run) >= minimum and run not in exceptions
        for run in _DIGIT_RUN.findall(name.fqdn)
    )


def numeric_exceptions(domains: Iterable[str]) -> frozenset[str]:
    """Digit runs found in legitimate domains, used to suppress M-04."""
    runs: set[str] = set()
    for domain in domains:
        runs.update(_DIGIT_RUN.findall(domain))
    return frozenset(r for r in runs if len(r) >= config.MIN_CONSECUTIVE_DIGITS)


# evaluation order = registry order (most informative first)
MORPHOLOGICAL_RULES: tuple[Rule, ...] = (Rule.M_01, Rule.M_02, Rule.M_03, Rule.M_04)


def evaluate_morphological(
    name: DomainName,
    digit_exceptions: frozenset[str] = frozenset(),
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled morphological rule as a Reason, or None."""
    predicates = {
        Rule.M_01: lambda: has_min_hyphens(name),
        Rule.M_02: lambda: registrable_too_long(name),
        Rule.M_03: lambda: has_min_labels(name),
        Rule.M_04: lambda: has_digit_run(name, exceptions=digit_exceptions),
    }
    for rule in MORPHOLOGICAL_RULES:
        if rules is not None and rule not in rules:
            continue
        if predicates[rule]():
            return Reason(family=Family.MORPHOLOGICAL, rule=rule, points=0)
    return None
