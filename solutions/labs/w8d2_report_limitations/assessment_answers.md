# W8D2 model answers

## Reasoning questions

1. **No.** Overlapping separate intervals do not show equivalence, and each test interval is wide because only 7
   recordings are resampled. Compute the paired difference with a cluster bootstrap over the same recordings,
   and compare it with a minimum practically important difference fixed in advance. Do it on development data,
   where the decision is made (27 recordings): +0.069 [0.022, 0.128] for logistic minus flow-rate z-score,
   "inconclusive" because the interval includes values below 0.05. The test look is reported, not used to choose.
   *Common wrong answer:* "overlap means no significant difference": it confuses two marginal intervals with the
   interval of the difference, and it ignores the pairing.
2. Zero events in about 1.2 hours is consistent with the budget and also with rates far above it: with a Poisson
   rate of one per 8 hours, the chance of no false alarm in 1.2 hours is about $e^{-0.15} \approx 0.86$. Sentence:
   "No false alarm occurred in about 1.2 hours of normal operation in the test recordings; this is too little to
   confirm the budget of one per 8 hours, which is monitored in operation." *Wrong answer:* "the model has zero
   false alarms".
3. Value-anywhere tracing proves a number *exists* in the results, not that it is the right one. Stricter options:
   tag numbers with the key they come from (a template that renders `{monitoring.drift_share_a:.0%}`), trace per
   section to a sub-tree of the results, or generate the prose (worked example). The checker is a floor.
4. The sentence protects the decision: without it, a reader may deploy on a real plant expecting benchmark
   performance. Removing it would make every number misleading, and if a reviewer finds the omission the project's
   credibility suffers more than from the caveat. Wording: "Evaluated on a laboratory testbed; a pilot on the
   plant's own data, with the same protocol, is the next step before relying on it."
5. A defensible choice: (a) 7 test recordings and 34 faults (bounds every claim); (b) laboratory testbed, unseen
   fault families (bounds where it applies); (c) drift is not degradation, labels arrive late (bounds how failure
   would be noticed). Other choices are fine if justified by the stakeholder's decision.

## Interview rep rubric (score 0-2 each)

| Element | 2 points if the answer... |
|---|---|
| Plain language | uses counts ("5 of the 7 faults we tested") and a range ("between about a third and nine in ten") |
| Cause | explains that 7 test faults is too few to pin the rate down, with an everyday analogy |
| Usefulness | says what the system is good for now (an early warning that supplements inspection) |
| Path forward | proposes how to get a reliable number (a pilot with logged faults; how many) |
| No jargon | avoids "confidence interval", "bootstrap", "PR-AUC" |

Strong answer: "We tested it on 7 recorded faults and it caught 5. With only 7, that is like judging a goalkeeper
on 7 penalties: the true rate could be anywhere from about one in three to nine in ten. So I cannot promise 70 %.
What I can say is that it caught most faults within about two minutes and raised no false alarms in our tests. If
you run it alongside your inspections for a few months and we log every confirmed fault, a few dozen faults would
narrow that range enough to plan on."
