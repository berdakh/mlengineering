# Hint 2 — suggested approach (no code)

## Lab

**Test signals.** With `fs = 256` and `N = 128` the FFT bins are 2 Hz apart. A tone at an even
frequency with any phase occupies exactly one bin, so its band power is exactly `A²/2` and
its RMS exactly `A/√2`. That is what lets you use `rel=1e-9`.

**rms.** Sine of amplitude ≠ 1 (try 0.5 and 3). Add the scaling law with a negative factor.
Both rms defects fail the sine test; only one of them fails the scaling law — work out which.

**line_length.** `[0, 1, 0, 1, 0]` has line length 4. What does a signed sum give?

**peak_to_peak.** Any all-positive array, e.g. `[3, 5, 4]`.

**band_power.**
- Parseval: noise plus a constant offset; integrate from 0 to *beyond* Nyquist because the
  upper edge is exclusive; compare with `np.var(x)` (population variance).
- One tone inside a band → `A²/2`; a tone outside → 0 with an **absolute** tolerance.
- Edge: a 40 Hz tone has zero power in `[10, 40)` and all of it in `[40, 70)`.
  Additivity (`[10,40) + [40,70) = [10,70)`) fails for the same defect on white noise.
- Offset: `band_power(x + 100, fs, 0, 40) == band_power(x, fs, 0, 40)` — the band must start
  at 0 Hz for a DC defect to be visible.

**fill_gaps.** `[0, 1, nan, 3, 4] → [0, 1, 2, 3, 4]`. Zero-filling gives a different array.

**ratio.** Two tones, amplitudes 1.0 (24 Hz) and 0.5 (92 Hz): `bp_low = 0.5`, `bp_high = 0.125`,
`ratio = 0.25`. An inverted ratio gives 4.

**build_feature_table.** Shuffle rows with a fixed `random_state`; compare `line_length`
(order-dependent) after sorting both tables by `(unit_id, window_id)`.

**load_windows.** Write a CSV without one required column into `tmp_path`; expect `ValueError`.

**split.** Ten units. (a) `set(train units).isdisjoint(set(test units))`. (b) Collect the
test-unit sets for seeds 0–9; require more than one distinct set.

**model.** In your frame, give label-1 windows a 92 Hz tone of amplitude 2 on top of a
24 Hz tone of amplitude 1, and let every unit have both labels. AUC is 1.0 on correct code;
with the wrong probability column it is 0.0. Assert `>= 0.9` and document why.

## Challenge

Build a table before writing tests: rows = spec clauses, columns = "on the boundary",
"just inside", "just outside". Then:

- clause 2: a score equal to the threshold; a NaN between two above samples;
- clause 4: a gap of exactly `merge_gap`, and of `merge_gap + 1`;
- clause 5: an event of exactly `min_samples`; and the *order* of 4 and 5 — fragments that
  are each too short but long enough once merged;
- clause 6: an event touching index 0; an event still open at the last sample; check `stop`;
- clause 8: each invalid parameter.

Finally add one randomised structural test (seeded): every returned event has
`stop - start >= min_samples`, starts and ends on an above sample, and consecutive events
are more than `merge_gap` apart.
