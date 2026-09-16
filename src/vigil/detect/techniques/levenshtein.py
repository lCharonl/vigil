"""Bounded Levenshtein distance for R-03: exact edit distance, or None past max_distance."""


def bounded_levenshtein(a: str, b: str, max_distance: int) -> int | None:
    """Return the edit distance between a and b, or None if it exceeds max_distance."""
    if abs(len(a) - len(b)) > max_distance:
        return None
    if len(a) > len(b):
        a, b = b, a
    previous = list(range(len(a) + 1))
    for i, cb in enumerate(b, start=1):
        current = [i] + [0] * len(a)
        for j, ca in enumerate(a, start=1):
            cost = 0 if ca == cb else 1
            current[j] = min(
                previous[j] + 1,  # deletion
                current[j - 1] + 1,  # insertion
                previous[j - 1] + cost,  # substitution
            )
        if min(current) > max_distance:
            return None
        previous = current
    return previous[-1] if previous[-1] <= max_distance else None
