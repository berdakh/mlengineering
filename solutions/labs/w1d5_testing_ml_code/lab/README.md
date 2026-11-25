# Reference test suite - w1d5 lab

`tests/` is one suite that passes on the correct `pumpwatch` package and fails on
all 14 injected defects in `labs/w1d5_testing_ml_code/checks/bugs.py`.
It is *a* solution, not *the* solution: any suite that passes the checks is acceptable,
and yours may well be shorter.

Run it against the lab's package:

    PYTHONPATH=labs/w1d5_testing_ml_code/lab/src python -m pytest solutions/labs/w1d5_testing_ml_code/lab/tests -q

Things worth comparing with your own suite:

* `signals.py` holds test signals whose frequencies fall exactly on FFT bins, which is
  what allows `rel=1e-9` instead of a tolerance chosen by trial and error.
* `test_line_length_of_ramp_and_zigzag` - the ramp alone does not detect the missing `abs`.
* `test_band_power_parseval_...` integrates to `FS / 2 + DF` because the upper band edge is exclusive.
* `test_seed_argument_is_honoured` - "same seed, same result" passes when the seed is ignored.
* `test_model.py` explains in its docstring why `auc >= 0.9` is acceptable *there*.
