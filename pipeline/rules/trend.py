"""Tier 2 primitive: rolling-window trend detection.

A single small function — the least-squares slope of a series of numbers
against their sample index. No numpy: it's four lines of arithmetic, and
skipping the dependency means this file has nothing to install.
"""


def slope(values):
    """Least-squares slope of `values` (units per sample).

    Positive = rising, negative = falling, 0 if there's nothing to fit.
    """
    n = len(values)
    if n < 2:
        return 0.0
    xs = range(n)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    return numerator / denominator if denominator else 0.0
