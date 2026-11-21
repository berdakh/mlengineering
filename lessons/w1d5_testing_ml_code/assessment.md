# w1d5 assessment

Answer in writing (`lab/ASSESSMENT.md` or your notes) **before** opening
`solutions/lessons/w1d5_testing_ml_code/assessment_answers.md`. Short answers: 2–5 sentences each.
About 15 minutes for Part A + B. Part C is the optional interview rep.

## Part A — reasoning questions

**A1.** A test computes `expected = np.sqrt(np.mean(x**2))` for random `x` and asserts
`rms(x) == pytest.approx(expected)`. Is this a useful test? What does it detect and what can it not detect?

**A2.** For each assertion, state the layer it belongs to (unit / integration-smoke / data
validation / statistical performance check) and whether it should block a merge:
(a) `set(train_units).isdisjoint(test_units)`
(b) `df["temperature_c"].between(-20, 150).all()` on today's ingested file
(c) `cv_auc_mean > 0.90` on the real training set
(d) `train_and_evaluate(tiny_separable_frame)["auc"] >= 0.9`

**A3.** `band_power(tone_25Hz, fs=256, low=10, high=40)` with `N=128` returns `0.4911`
instead of the `0.5` you expected, so your test with `rel=1e-9` fails on the correct
package. Explain the cause and give two ways to repair the *test* — one good, one bad — and say which is which.

**A4.** Your suite has 100 % line coverage of `features.py`. A colleague concludes the
feature code is correct. Give a concrete counter-example from today's lab.

**A5.** The test "same seed → same split" passes. Which two defects in
`group_train_test_split` can still be present? Which additional test detects each?

**A6.** In w1d3 the scaler was moved inside a `Pipeline` to stop it from seeing test rows.
Why is that leak hard to catch with a unit test of `train_and_evaluate`, and what does this
tell you about the limits of testing as a control?

## Part B — explain a design choice (required)

**B1.** The checks run your suite from a temporary directory, without network, and the lab
forbids reading `data/synthetic/pump_vibration.csv` in unit tests. Argue for this constraint
as if a teammate had asked "why can't my tests just use the real file — it's more realistic".
Include what you would do instead to get the realism they want. (5–8 sentences.)

## Rubric for open-ended answers (A3, A6, B1)

| Level | Description |
|---|---|
| 0 — missing | Restates the question, or the claim is wrong. |
| 1 — partial | Correct conclusion, mechanism missing or vague ("floating point", "tests should be isolated"). |
| 2 — sound | Correct mechanism stated precisely, with the specific quantity or failure involved (e.g. "25 Hz is between 2 Hz bins, so power leaks outside the band"). |
| 3 — transferable | Level 2, plus a tradeoff or boundary of the rule (when you *would* use real data / a loose tolerance / a different control) and what you would do instead. |

Target: level 2 on every item, level 3 on B1. Anything below 2 → set *review needed* and re-read the linked handbook section.

Rubric for your **test code** (lab and challenge; self-assessed or reviewed):

| Criterion | Meets | Does not meet |
|---|---|---|
| Independent oracle | expected values derived from math/spec and auditable in the test | values pasted from the function's output |
| Discrimination | each test names (in title or comment) what wrong behaviour it rules out | "it works" tests |
| Tolerance | tight where exact, loose only with a stated reason | uniform loose tolerance |
| Isolation | no shared mutable state, no cwd/network/file dependence, seeded randomness | order-dependent or environment-dependent |
| Readability | one behaviour per test, parametrised instead of copy-pasted | a single 80-line test |

## Part C — interview rep (optional, 15 minutes, timer on, no hints, no references)

> **Prompt.** Implement `merge_intervals(intervals)`. Input: a list of half-open integer
> intervals `(start, stop)` with `start < stop`, in any order. Output: the sorted list of
> merged intervals, where intervals that overlap **or touch** (`a.stop == b.start`) are
> merged. Then write the tests you would want before shipping it. Talk through (write down)
> the boundary cases before you code.

Deliverable: one file with the function and its tests. Afterwards compare with
`solutions/lessons/w1d5_testing_ml_code/interview_rep/` and score yourself:

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Clarified the contract first (touching? unsorted? empty? input mutated?) | no | some | all four |
| Correctness | fails basic cases | fails a boundary | passes reference tests |
| Tests | none / happy path | some boundaries | boundaries + a property (output sorted, disjoint, same covered set) |
| Complexity stated | no | — | O(n log n) and why |
| Time | > 25 min | 15–25 min | ≤ 15 min |

Assistance for this rep is intentionally lower than in the lab: no starter code and no
hints. Record the score in your progress notes; these reps recur and the trend is the evidence.
