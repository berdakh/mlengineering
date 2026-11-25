"""zscorelib 1.0.0 (SYNTHETIC teaching package): calibrate a z-score from burn-in values."""
import math

__version__ = "1.0.0"


def calibrate(values):
    """Return (mean, standard deviation) of ``values``. The SD is the population SD (divide by n)."""
    values = [float(v) for v in values]
    n = len(values)
    mean = sum(values) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in values) / n)
    return mean, (sd if sd > 0 else 1.0)
