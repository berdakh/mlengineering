# Assessment answers - w3d3

## Reasoning questions

**1.** Upward. 0.868 is the maximum of 24 noisy estimates; the configuration was chosen partly because its
fold scores were favourable. The bias grows with the noise of each estimate (σ, about the SE ≈ 0.03
here), with the number of candidates K (≈ σ·E[max of K], roughly σ√(2 ln K) for many near-equal
candidates), and shrinks with the correlation between candidates' errors (√(1−ρ); shared folds make it
smaller) and with real spread in true quality. In the lab's real run the best trial's dev score was 0.868;
the nested estimate of the procedure was 0.744 ± 0.036.
*Common wrong answer:* "it is unbiased because CV is unbiased" - CV is (nearly) unbiased for a *fixed*
configuration, not for one selected by the same CV.

**2.** The outer loop does not wrap the selection: every fold used to report the score also voted for the
configuration. The procedure estimates the CV score of the configuration selected on these same folds,
i.e. the optimistic number of question 1 again (with a fresh fold-assignment noise added if the folds
differ). The mutant `outer_fold_in_inner_search` implements exactly this and is rejected by the poisoned-
fold test.

**3.** Not a bug. Each outer fold runs the search on different inner data; the choice changes because the
candidates are not separable with 18-19 development experiments: their differences are within the noise.
The report should give the nested estimate of the *procedure* and say the choice was unstable; quoting the
dev score of the finally selected configuration would hide that.

**4.** With 32 trials a grid over 5 dimensions gives 2 values per dimension (2^5 = 32), so an important
dimension is explored at two points; random search gives 32 distinct values in every dimension, which
matters because typically only one or two dimensions drive performance. Log scale: regularisation
strength C or alpha, learning rate, minimum samples per leaf (often), tolerance; linear scale: fractions
such as subsample in [0.5, 1].

**5.** In-sample scores are separated more cleanly than scores on new experiments (the model has fitted
those rows), so the best-F1 threshold is miscalibrated for new data, typically too extreme. The lab scores
every development row by a model trained without that row's fold (`out_of_fold_scores`), chooses the
threshold on those, freezes it, and applies it once to test.

**6.** That the test set was used twice and the reported score was obtained after a change prompted by
the first test result; it is therefore optimistic (a selection between "before" and "after" on test) and
is no longer an unbiased estimate. Fixing a genuine bug is right; the honest options are to report both
numbers with that statement, or to re-evaluate on data not yet used. Silently replacing the number is
the failure.

## Design-choice explanation - what a strong answer contains

* In the real run the top trials' SEs (~0.029) exceed the spread among the top few means (0.868 vs 0.859),
  so their ordering is noise; the one-SE rule picked trial 12 (50 boosting iterations) over trial 17 (200).
* Complexity ordering justified operationally: linear before boosted (latency, interpretability, simpler
  artifact), shorter windows before longer (less warm-up and shorter delay online, w5d3), stronger
  regularisation and fewer/shallower trees first (variance, inference cost).
* What it does not fix: the chosen candidate's dev mean is still optimistic; the reported number comes
  from the nested estimate. It also does not protect against the test set being looked at more than once.
* A strong answer notes that with four folds the SE itself is noisy.

## Interview rubric (ML fundamentals)

| Level | Description |
|---|---|
| Strong | L2: penalty is rotation-invariant and strictly convex, so for correlated features the minimiser spreads weight across them (identical features get equal weights); L1: the diamond's corners lie on axes, so the solution tends to land where one coefficient is zero; mentions the elastic net as a compromise. Bias rises and variance falls with regularisation; choose by grouped CV with the one-SE rule, noting the SE with few groups. |
| Adequate | Correct qualitative answers without the geometric or optimality argument. |
| Not yet | Claims L2 zeros coefficients, or chooses the strength on the test set. |

## Challenge: reference reading

See `challenge/REPORT.md` in this directory for numbers (trial 54, pre-look estimate 0.736, one look
0.7083, the optimism table). Rubric for the written parts:

| Element | Demonstrated when |
|---|---|
| Rule | Stated before looking; justified by the noise level of the table (SE vs spread of top means), not by the test score. |
| Estimate | Not the chosen trial's dev mean; computed by re-applying the whole rule without each fold (or an equivalent bias correction) and justified. |
| The look | Exactly one; the gap to the estimate is put in numbers and compared with plausible noise; no switch after looking. |
| Simulation | An expectation is written before running; the table varies K and ρ (or σ); the result is compared with the expectation. |
| Limits | At least two: one table proves nothing about a procedure; the generator's assumptions (exchangeable trials, noisier complex models) need not hold for real searches. |
