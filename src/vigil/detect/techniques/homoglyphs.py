"""Detects homoglyph / bitsquat / IDN-confusable substitutions against a watched domain.

This module will be responsible for recognising when an observed domain visually or
byte-wise impersonates a watched domain via Unicode confusables (e.g. Cyrillic "а" for
Latin "a"), punycode tricks, or single-bit-flip ("bitsquatting") variants. It compares
two domain strings — it does not touch CertEvent or Finding.
"""


def is_homoglyph_match(candidate: str, watched: str) -> bool:
    """Return True if `candidate` is a homoglyph/bitsquat/confusable of `watched`.

    Not implemented: this is where the detection logic will live.
    """
    raise NotImplementedError
