# w6d6 assessment

Answer in writing (or aloud, recorded) before opening
`solutions/lessons/w6d6_cd_ops_debugging/assessment_answers.md`. About 25 minutes.

## Reasoning questions

1. **Rebuilds.** Three builds of the same commit gave three different digests in the authoring run. Why
   does that matter for "it passed in staging"? What is promotion doing instead of rebuilding?
2. **Rollback scope.** For each of the three lab incidents, say whether `rollback.py --apply` would have
   fixed it, and what it would have done instead.
3. **Two validation layers.** Why does the service *exit* on `FLOWGUARD_MODEL_DlR=...` but *keep running,
   not ready* when `FLOWGUARD_MODEL_DIR` points at a directory that does not exist?
4. **Exit 137.** The OOM-killed container's logs end with a normal startup line. Where does the evidence
   for the cause come from, and why is it not in the logs?
5. **"Good" too early.** The memory incident briefly answered `/readyz` with 200. What rule for marking a
   deployment good would have caught it during the deployment, and what does that rule cost?
6. **History file.** Why does `select_rollback_target` sort by `deployed_at` instead of trusting list order?
   Give a realistic way the list could be out of order.

## Design-choice explanation (150-250 words)

7. The deploy tool pins production to `image@sha256:...` and stores configuration in env files outside the
   image. A colleague proposes baking the production environment file *into* a separate "production image"
   so that "the image is the whole truth". Argue for or against for this service, and name the strongest
   point of the side you reject.

## Interview rep (10-15 minutes, debugging narrative, reduced assistance)

> "Tell me about a time a system you were responsible for failed in a way that was hard to diagnose. What
> did you see first, what did you think it was, what did you check, and what was it really?"

Answer with one of this lab's incidents (or a real one from your research systems) in the structure
symptom - first hypothesis - the test that changed your mind - cause - fix - what you changed afterwards.
Speak for 5 minutes, then answer the follow-up "how would you make sure it cannot happen again?" for 2
minutes. Score yourself with the rubric in the answers file afterwards.

## Rubric (self-assessment)

| Score | Meaning |
|---|---|
| 2 | Correct, uses the mechanism (digest, readiness, cgroup OOM, append-only history) and a concrete consequence |
| 1 | Right conclusion with a vague reason |
| 0 | Wrong, or treats rollback as a universal fix |

Questions 1-6: 2 points each; question 7: 4 points. 12+ of 16: move on. Below 9: redo task 5 with the
scenarios in a different order a day later, without your DEBUG_LOG open.
