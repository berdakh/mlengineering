# W2D5 assessment

Write answers before opening `solutions/lessons/w2d5_feature_pipeline/assessment_answers.md`.
Three to six sentences each unless stated. Questions 1–6 take about 15 minutes.

## Reasoning questions

**Q1.** A rolling mean of length *w* = 40 monitors a signal with white noise of standard
deviation 0.8. A fault adds a step of 1.2. The alert threshold on the mean is 0.6.
(a) Expected detection delay in samples? (b) Standard deviation of the fault-free rolling mean,
and the threshold in units of it? (c) The noise turns out to be AR(1) with φ = 0.8. Without
simulating, what happens to (b), roughly by what factor, and what follows for the false-alert rate?

**Q2.** Your feature function passes the look-ahead perturbation test. A colleague concludes
the offline evaluation is now free of temporal leakage. Give two different ways the evaluation
could still use future information that this test cannot see.

**Q3.** `df["z"] = df.groupby("experiment_id")["pressure"].transform(lambda s: (s - s.mean()) / s.std())`
is proposed as a robust way to remove between-experiment offsets. State precisely what is wrong
with it for a deployed detector, and give a causal alternative that still removes offsets,
with its main assumption.

**Q4 (design choice).** For warm-up rows this unit returns NaN and a `rows_since_reset`
column instead of partial-window values. Defend or attack that choice for (i) an offline
training table and (ii) an online service that must return a score for every reading from the
first second. Say what you would do in case (ii) and what it costs.

**Q5.** The cache key uses a hand-maintained `FEATURE_VERSION`. Describe one concrete sequence
of events in which this serves stale features, and one in which using the git commit hash
instead would be worse. Which would you choose for this project and why?

**Q6.** In worked example 3.2 the centred window changed pooled average precision by at most
0.014, while the choice of reference rows changed it by about 0.23. Someone proposes dropping
the causality requirement "since it does not matter on this dataset". Respond, using what the
metric in that table can and cannot measure.

## Rubric (per question)

| Level | Description |
|---|---|
| Not yet | Restates the lesson, or the answer is wrong in mechanism (e.g. treats leakage as a metric-size question) |
| Partial | Correct mechanism but no quantity where one was asked, or only one of two requested cases |
| Solid | Correct mechanism, quantities right to within rounding, names the assumption or the cost |
| Strong | Additionally states what evidence would change the answer, or connects to deployment behaviour (delay, state, monitoring) |

Evidence of independent skill for this unit needs "Solid" on Q1, Q3 and Q4.

## Interview rep — Python coding (15 minutes, timed)

Assistance level for Week 2: attempt untimed first if the timed attempt fails; rubric and a
reference are available afterwards in the solutions folder.

> Implement `sliding_max(values, w)` returning, for every index `i >= w - 1`, the maximum of
> `values[i-w+1 : i+1]`, in O(n) total time. Then implement a class `StreamingStats(w)` with
> `update(x) -> (mean, variance)` over the last `w` values in O(1) time per update and O(w)
> memory (population variance; before `w` values have arrived, use those seen so far).
> State the complexity of each and name one numerical risk in your `StreamingStats`.

Say your approach aloud before coding. Write at least three tests yourself, including one
adversarial input for each function.
