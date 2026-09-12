"""Generates candidate typosquatting permutations of a watched domain.

This module will be responsible for producing the set of strings a defender expects
an attacker might register when squatting on a monitored brand: character insertion,
omission, transposition, substitution, common misspellings, TLD swaps, combosquatting,
etc. It takes a clean domain name and yields variant strings — it does not touch
CertEvent or Finding, and does not itself decide whether an observed domain matches.
"""

from collections.abc import Iterator


def generate_permutations(domain: str) -> Iterator[str]:
    """Yield typosquatting permutations of `domain` (character-level edits, TLD swaps, ...).

    Not implemented: this is where the detection logic will live.
    """
    raise NotImplementedError
