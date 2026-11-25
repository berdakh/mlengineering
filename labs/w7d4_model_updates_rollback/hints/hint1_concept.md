# Hint 1 (concept): every step must be reversible and must not lie

* **Gate.** The two models must be compared on the same experiments, resampled together. Write the
  decision as a rule you could have written before seeing any numbers: policy, margin, guardrail, slices.
* **Shadow.** Serving is sacred. Whatever the candidate does (raise, hang, modify its input), the
  response is the current model's, computed on untouched data.
* **Promote.** Check everything that could make the new version unservable *before* moving the pointer.
  Then move it in one atomic step. Only then write down that you moved it.
* **Rollback.** "Previous" is not "the last line of the log": a rollback followed by another rollback
  must not re-deploy the version you just removed. Think of promotions as a stack.
