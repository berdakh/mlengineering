# Challenge — a comparison protocol you could defend, and a verdict rule that respects both uncertainties

Independent work: no hints are provided for the challenge beyond the lesson's own hint files, and the
reference solution is not in this folder. Aim for 45-60 minutes.

## Part A — `seedcompare.py` (graded by checks)

Implement the three functions in `challenge/seedcompare.py`. Inputs are per-seed values of ONE metric
on ONE fixed evaluation set, as a mapping `{seed: value}`.

1. `seed_summary(values) -> dict` with keys `n`, `mean`, `sd`, `min`, `max`.
   * `sd` is the **sample** standard deviation (ddof = 1).
   * Fewer than two seeds raises `ValueError` (one run carries no information about seed variance).
   * Any non-finite value raises `ValueError` (a diverged or crashed run is reported, not averaged).
   * A deterministic detector reported with several identical values has `sd` 0 (up to rounding).

2. `compare(a, b, test_halfwidth) -> dict` comparing detector A with detector B. Return at least
   `a` and `b` (the two summaries), `difference` (mean A minus mean B), `seed_se`, `margin`, `verdict`.
   * `seed_se = sqrt(sd_a^2 / n_a + sd_b^2 / n_b)`.
   * `margin = max(2 * seed_se, test_halfwidth)`, where `test_halfwidth` is the half-width of a 95%
     test-set interval for the difference (for example from w3d5's paired cluster bootstrap).
   * `verdict` is `"A better"` if `difference > margin`, `"B better"` if `difference < -margin`,
     otherwise `"cannot tell"`.
   * A negative or non-finite `test_halfwidth` raises `ValueError`.

3. `format_table(rows) -> str`: a Markdown table with one row per detector, columns detector, seeds,
   mean ± sd, range.

```bash
python wb.py check w4d3 --challenge
```

## Part B — `PROTOCOL.md` (rubric-graded)

A colleague proposes replacing the plant's current-threshold alarm with a transformer trained on raw
1 kHz motor-current waveforms from 40 pumps (12 of which had a bearing failure in the last two years).
Write `challenge/PROTOCOL.md` (at most one page) specifying the comparison you would require before the
switch:

* the unit of splitting and what is held out; what is read only once;
* what is held equal between the two detectors (data, rows scored, metric, tuning budget, stopping rule)
  and what cannot be held equal, stated as such;
* how many seeds, which uncertainties are reported and how they enter the decision (your Part A rule or
  a better one, justified);
* the cost and operational criteria that count besides accuracy;
* the decision rule written before seeing the results, including what "cannot tell" leads to.

## Acceptance criteria

* Part A: all challenge checks pass.
* Part B: scores at least "solid" on every row of the rubric in `assessment.md` (section C).
