# W4D5 assessment: model answers

## Reasoning questions

**1.** It is **inconclusive**. The interval excludes zero, so B is probably somewhat better. But its
lower end (+0.004) is below the MPID (+0.02), so the data do not show that the gain is large enough
to matter. For the product owner: "B is probably a little better, but we cannot show it is better by
enough to change outcomes; on this evidence it does not earn its extra cost."
*Common wrong answers:*
* "Better, because it excludes zero." This confuses detectable with important.
* "Equivalent." The interval reaches above +0.02, so it is not wholly inside the band.

**2.** If the MPID is chosen after seeing the results, it becomes a free parameter that can be set
to deliver the preferred conclusion. With an interval of [+0.03, +0.09], for example, choosing an
MPID of 0.025 lets you declare B "practically better". The MPID should come from the decision (what
change in outcome is worth acting on) and from someone who has not seen the numbers. This is the
same garden-of-forking-paths problem as tuning on the test set (w3d3).
*Wrong:* "So the result looks objective." That is a reason, but not the mechanism.

**3.** Right: no candidate off the front should be chosen, because each is beaten on every
objective by some candidate on the front. Wrong: the front does not make the remaining candidates
interchangeable. Choosing among them needs a preference (MPID, hard constraints, complexity
ranking), and the candidates differ in ways the objectives may not capture: retraining needs,
interpretability, dependencies.

**4.**
* The mean hides the tail: p95 and p99 are what hit timeouts.
* Warm-up calls (lazy imports, allocation, cold caches) are mixed into the sample.
* The loop measures a different workload: a hot loop on one host with no contention, no
  serialisation and no network. Batch size may differ from production, and thread oversubscription
  on a busy host can change the result by orders of magnitude (the worked example went from 3.5 ms
  to 8 s).
* Also acceptable: the clock used (`time.time` is not monotonic), and measuring a different object
  from the one deployed.

**5.**
* (a) The test set is for one look at the *chosen* model; choosing by test results turns it into
  selection data (w3d3).
* (b) The difference (0.017) is below the MPID of 0.05.
* (c) With 7 test experiments the interval for such a difference is very wide (w3d5), so the
  ordering could easily flip.
* (d) The choice also rests on costs and retraining needs, which the test score does not change.

**6.** `sys.getsizeof` returns the size of the Python object header, not of the objects it refers
to (arrays, trees, dictionaries). Serialise the deployed artifact the way it will be shipped and
measure the file (`model_size_bytes`). For memory at run time, measure resident memory after loading
it, for example with `tracemalloc` or the process RSS.

## Design choice: a model answer

The ordering ranks what is expensive to *own*, not what is expensive to compute. The isolation
forest is large and slow, but it retrains itself from the first 100 normal rows of every run:
nobody has to do anything, and its cost is mostly CPU, which is cheap at one sample per second. The
logistic model is tiny, but retraining it needs labelled faults. In maintenance these are the
scarcest data: each label comes from an incident someone investigated. Its behaviour also changes
whenever the fault mix in the labels changes, so every retrain needs a fresh validation like this
lesson's. The supervised model also brings a labelling pipeline, a training job and a model
registry entry, which the per-run detectors do not need. A defensible alternative ranks by run-time
cost (forest above logistic) when the deployment target is a constrained edge device. The point of
the exercise is that the ranking must be argued from the operational context and written down
before the results.

*Common weak answers:*
* Ranking by parameter count or file size alone.
* Not mentioning where retraining labels come from.

## Interview rep: rubric and worked answer

| Criterion | 0 | 1 | 2 |
|---|---|---|---|
| Opens with the decision rule, not the numbers | no | partly | "we fixed an MPID and a complexity ranking before comparing" |
| Uses the interval correctly | quotes point estimates | mentions an interval | "+0.07 [+0.02, +0.13]: detectable, not shown to exceed +0.05" |
| Names costs beyond accuracy | none | one | labels for retraining, interpretability for the engineer, extra pipeline |
| Keeps the test set clean | uses test to argue | unclear | "the test set confirmed the chosen model once" |
| Says what would change it | nothing | vague | "15 more labelled faults and an interval wholly above +0.05" |
| Time | > 3 min or < 45 s | 2-3 min | 1-2 min |

*Worked answer (about 90 s).* "Before comparing, we fixed a minimum difference worth acting on,
+0.05 PR-AUC, and a complexity order, with models that need labelled faults to retrain at the
expensive end. On development data, with a paired bootstrap over experiments, the logistic model was
+0.07 better, but the interval went down to +0.02. So it was not shown to be better by enough to
justify needing labelled faults for every retrain, and the alarms would have been harder for the
engineer to interpret. The rule then says: take the simplest candidate not shown to be worse, which
was the flow-rate z-score. We looked at the test set once, for that model. (a) +0.07 is the point
estimate; the evidence is the interval. (b) I'd switch when we have about 15 more labelled faults
and the interval is wholly above +0.05, or if we meet a fault family that flow rate does not see."
