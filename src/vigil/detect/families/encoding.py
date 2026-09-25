"""Encoding family (E-01..E-02): mixed-script and punycode labels."""

import unicodedata

from vigil.detect.data import thresholds
from vigil.detect.registry import Family, Rule
from vigil.detect.techniques.names import DomainName
from vigil.models import Reason


def _label_scripts(label: str) -> set[str]:
    """Unicode scripts of the alphabetic characters in a label."""
    scripts: set[str] = set()
    for char in label:
        if not char.isalpha():
            continue
        char_name = unicodedata.name(char, "")
        if char_name:
            scripts.add(char_name.split(" ", 1)[0])
    return scripts


def _decode_label(label: str) -> str:
    """Decode a punycode label to Unicode; return it unchanged if it isn't valid punycode."""
    if not label.startswith(thresholds.PUNYCODE_PREFIX):
        return label
    try:
        return label.encode("ascii").decode("idna")
    except UnicodeError:
        return label


def has_mixed_script_label(name: DomainName) -> bool:
    """E-01: a single label mixes characters from more than one Unicode script."""
    return any(len(_label_scripts(_decode_label(label))) > 1 for label in name.labels)


def has_punycode_label(name: DomainName) -> bool:
    """E-02: a label is punycode-encoded."""
    return any(label.startswith(thresholds.PUNYCODE_PREFIX) for label in name.labels)


ENCODING_RULES: tuple[Rule, ...] = (Rule.E_01, Rule.E_02)


def evaluate_encoding(
    name: DomainName,
    rules: frozenset[Rule] | None = None,
) -> Reason | None:
    """Return the first matching enabled encoding rule as a Reason, or None."""
    predicates = {
        Rule.E_01: lambda: has_mixed_script_label(name),
        Rule.E_02: lambda: has_punycode_label(name),
    }
    for rule in ENCODING_RULES:
        if rules is not None and rule not in rules:
            continue
        if predicates[rule]():
            return Reason(family=Family.ENCODING, rule=rule, points=0)
    return None
