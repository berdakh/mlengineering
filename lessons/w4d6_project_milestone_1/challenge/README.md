# W4D6 challenge: submit milestone 1 for review

**Conditions for "independent skill demonstrated":** your own repository, no hints, and a reviewer
(the course author or a peer) agrees with your self-review within one point on every row.

1. In your flowguard repository, make sure `make evaluate` builds the report from a fresh clone (after
   `python project/get_skab.py`). Commit, then build, so the provenance shows a commit without `-dirty`.
2. Fill in `lessons/w4d6_project_milestone_1/challenge/SUBMISSION.md`:
   * the header fields;
   * every checklist item, ticked or marked n/a with a reason;
   * a self-review score (1-3) with evidence for each rubric row in `../assessment.md`;
   * at least one specific question for the reviewer.
3. `python wb.py check w4d6 --challenge` checks the structure only:
   * no TODOs;
   * a commit hash that is not dirty;
   * a complete checklist;
   * scores with evidence of at least one sentence;
   * a question.
4. Commit and push the submission (and your report), then send it for feedback. Expect comments on
   the evidence, not on the formatting.

What the reviewer looks at first:
* Does a clean rebuild reproduce your committed report byte for byte?
* Can every number in your Results tables be found in `results.json`?
* Does your Decision section follow from your table by the rule you stated?
