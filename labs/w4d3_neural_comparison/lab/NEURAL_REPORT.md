# Neural versus classical on SKAB: report

Fill this in after `python labs/w4d3_neural_comparison/lab/compare_seeds.py`. Paste numbers from
your own run; do not copy the lesson's.

## Set-up actually used

* Python / torch / NumPy versions:
* torch threads (from the script's output JSON):
* Machine (CPU model if you know it):

## Results

Paste sections 2-4 of the script's output here.

```text

```

## Questions

1. Which uncertainty is larger here, the seed spread of the neural model or the test-set interval of
   one fitted model? What does that imply for how many seeds are worth running?

2. On VAL the chosen autoencoder beats every Mahalanobis setting; on TEST it does not. Give two
   explanations that are consistent with the numbers, and say which data would distinguish them.

3. Which seed would you ship if you had to ship a neural model, and why is "the seed with the best
   TEST score" not an acceptable answer?

4. Recommendation for the project (3-5 sentences): which detector goes forward to Week 5, what claim
   about the neural model the evidence supports, and what you would need to revisit that decision.
