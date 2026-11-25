# Hint 1: concept

* **Latency.** You need two clocks readings per *timed* call, none for warm-up calls. Store
  durations only for the calls after warm-up, then take percentiles of those.
* **Dominance.** Turn every objective into "larger is better" first (multiply min-objectives by -1).
  After that, dominance is one line. Equality on everything is *not* dominance.
* **Practical difference.** Compare the interval's *ends* with ±MPID, never its middle. Four cases;
  "inconclusive" is whatever is left over.
* **Recommendation.** Two filters (hard constraints, then "better" or else "not worse"), then a sort
  by complexity. The primary metric only breaks ties in complexity.
* **Challenge.** What is the independent unit in the churn data? Resample *that*, and apply the same
  draw to both models.
