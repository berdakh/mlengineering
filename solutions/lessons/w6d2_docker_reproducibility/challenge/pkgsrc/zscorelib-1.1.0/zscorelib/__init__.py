"""zscorelib 1.1.0 (SYNTHETIC teaching package): calibrate a z-score from burn-in values.

Changelog 1.1.0: ``calibrate`` now returns the sample standard deviation (divide by n - 1),
"for consistency with statistics.stdev". A minor release, so ``zscorelib>=1.0`` accepts it.
"""
import math

__version__ = "1.1.0"


def calibrate(values):
    """Return (mean, standard deviation) of ``values``. The SD is the sample SD (divide by n - 1)."""
    values = [float(v) for v in values]
    n = len(values)
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / (n - 1))
    return mean, (sd if sd > 0 else 1.0)
