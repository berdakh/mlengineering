# w5d6 assessment — model answers

## 1. Why three-way parity

Two paths that share code agree even when the shared code is wrong. Example (the
`batch_global_burn_in` mutant): `score_experiments` calibrates every experiment on the first 100 rows of
the *whole table* instead of its own first 100 rows. `experiment_scores` calls `score_experiments`, so
evaluation and batch agree to the last bit; the report and the nightly batch job are both wrong in the
same way. The API receives a per-experiment burn-in from the client and computes the correct score, so
only a comparison that includes the API sees the difference. Comparing all three (or each path against
an independent reference) closes this gap.

*Common wrong answer:* "two-way is enough if the tests are good". Unit tests of the shared function with
a single experiment cannot see a per-experiment selection bug either.

## 2. Tolerance and the CSV round trip

The checks use an absolute tolerance of 1e-9 on scores of order 1-100; any real skew (ddof: 0.5 % at
n = 100) is many orders larger, while representation noise is about 1e-14. On the real data, reading the
batch CSV with pandas' default float parser gave differences up to 5.7e-14 on 20,708 of 46,806 rows even
though the file holds 17 significant digits; `float_precision="round_trip"` made them exactly 0. Either
choose a tolerance far above representation noise and far below meaningful skew, or make the round trip
exact and compare exactly; know which you are doing.

## 3. The manifest hash in the bundle

It answers "was this model built from the same split, and hence the same development data and the same
untouched test set, as the evaluation report?" The milestone-1 report prints `a9f4e243...5314`; the
bundle records the same value. Reviewers use it to accept the release; an on-call engineer or auditor
uses it months later to tie the deployed artifact to its evidence; the team uses it to notice that a
rebuilt model was silently built from an edited manifest.

## 4. Chunking

The score of each value depends only on that value and on the burn-in statistics (mean, population
std); values do not interact. Sending the same burn-in with every chunk therefore gives exactly the
batch scores (verified: maximum difference 0.0 on all 35 experiments). Chunking breaks for any model
with state across values: rolling-window features, AR residuals, CUSUM, a recurrent network, or
event post-processing (`min_duration`, `merge_gap`). There the client must send overlapping context or
the server must keep per-stream state (w5d3, streaming scorer), and parity must be tested at chunk
boundaries.

## 5. Three versions

* **Package** (semantic version of the code): a new CLI subcommand or a bug fix in the loader -> 0.6.0 to
  0.6.1 or 0.7.0; the model and API schema do not change.
* **API schema** (`flowguard-api/1`): renaming `scores` or making a new field required -> `flowguard-api/2`,
  served alongside v1 (w5d5 policy); the model can stay the same.
* **Model** (`flowrate-z-2026.11`): a new threshold for a stricter alert budget -> new model version; code
  and API unchanged.

## Design choice

**For packaging a reviewed configuration:** the threshold is a decision with evidence (w4d5 memo,
milestone-1 report); rebuilding should reproduce that decision, not make a new one silently. Builds are
fast and deterministic, and a reviewer approves one number. Provenance must then record the config file
and its hash, and the manifest hash that links it to the report.

**For re-choosing at build time:** the threshold is a function of data and the alert budget; computing
it in the build keeps code, data and decision in one reproducible step, and a data update produces an
updated threshold without hand edits. Provenance must then record everything the choice depended on:
manifest hash, a hash of the development data, the alert budget, the selection rule and code version,
and the chosen value, and the build must fail if the chosen value differs from the reviewed one without
an explicit approval.

**A good answer** says the choice depends on how often the data changes and who must approve a new
operating point, and notes that in both cases the evaluation report must be regenerated from the same
artifact.

## Interview rep: checklist for a strong answer

1. Client sends `POST /predict` with `burn_in` and `values` (JSON); uvicorn passes it to the ASGI app.
2. pydantic validates: types, finite numbers, sizes, no unknown fields; invalid -> 422 with
   `{loc, msg, type}`, nothing echoed.
3. The endpoint checks the model is loaded (else 503) and the batch size (else 413).
4. The model was loaded once at startup from a bundle whose checksums were verified; `/readyz` reported
   ready only after that.
5. `ZScoreModel.score` computes |x - mean(burn_in)| / population std; flags are score >= threshold 7.24.
6. Response: model version, threshold, one score and flag per value.
7. **How I know it matches the report:** the same function computes evaluation, batch and API scores; a
   parity test runs on every change; on the real data the three agree exactly over 46,806 rows; the bundle
   records the split-manifest hash printed in the report.
8. Limits: it trusts the client's burn-in to be normal operation; point flags, not events (post-processing
   is not in the API); seven test experiments.

Points 1-6 alone describe a working API; point 7 is what distinguishes an engineer who has thought about
training/serving skew.
