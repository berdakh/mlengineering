# Mutant: centred_window

The rolling mean/std/min/max use `center=True`. Offline this looks better (smoother, better aligned with the label edges) and every value test on a single frame still looks plausible, but each feature at row *i* now contains about `w/2` future rows. In deployment those rows do not exist yet. Typical cause: copying a smoothing line from exploratory plotting code. Caught by the look-ahead perturbation test and by the slow-reference comparison.

Changed file: `src/flowguard/features.py`
