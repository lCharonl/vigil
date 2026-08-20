"""Scores and explains matches between an observed certificate and the watchlist.

This module will be responsible for turning a raw match (from permutations.py or
homoglyphs.py) plus the surrounding CertEvent into a Finding: a score in [0, 1] and a
list of human-readable reasons. It is the only detect module allowed to construct a
Finding.
"""

from vigil.models import CertEvent, Finding


def score_match(cert: CertEvent, matched_watch_target: str) -> Finding:
    """Compute a Finding (score + reasons) for `cert` against `matched_watch_target`.

    Not implemented: this is where the detection logic will live.
    """
    raise NotImplementedError
