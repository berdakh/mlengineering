# w8d5 challenge - a project of your own, told for an engineering audience

**Independent. No hints, no solutions until you have finished.**

Pick one project you led or contributed substantially to: a research or thesis project, a course
project, or work from a job or internship. In `challenge/`:

1. `RESEARCH_WALKTHROUGH.md` - a 5-minute walkthrough with the six beats (Problem, Constraint,
   Decision, Evidence, Limitation, Next step; 550-800 words in those six sections, each at least 40),
   plus two further sections:
   * `## Translation to industry` (at least 60 words): the same structure in an industrial setting,
     and what an engineering role would add that the study never needed.
   * `## What was not established` (at least 40 words): claims your evidence does not support.
2. `ADVERSARIAL.md` - five questions a sceptical interviewer would ask about that project (`## A1` ...
   `## A5`), each answered with lines starting `Question:`, `Concede:`, `Quantify:`, `Redirect:`;
   each answer at most 120 words.

Rules: use only numbers you can source from your paper or data. If the study reported no interval,
write "no interval" and why, rather than inventing one. Do not include unpublished or confidential
details you would not say in an interview.

## Acceptance criteria

* `python wb.py check w8d5 --challenge` passes (structure only).
* Rubric in `../assessment.md` ("Research walkthrough" rows): the translation names concrete
  counterparts (unit, event, error costs) and at least two engineering concerns absent from the study.
* Recorded once; `python wb.py mark w8d5 independent` only if written without hints.
