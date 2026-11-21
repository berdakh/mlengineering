# Mutant: closed_both_ends

The window is [tau - w, tau] instead of (tau - w, tau]: an observation exactly w seconds old is included. On irregular timestamps the difference is invisible; on regularly spaced data every window holds one extra row. Caught by the boundary test and the seconds-not-rows test.

Changed file: `timefeatures.py`
