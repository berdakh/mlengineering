# w8d3 challenge — review a flawed design (45 minutes, timed)

**Task.** Read [`DESIGN_DOC.md`](DESIGN_DOC.md), a colleague's draft design for routing support tickets with
a model. Write your review in [`REVIEW.md`](REVIEW.md): a findings table, a verdict and a short summary.
Treat it as a real review: the author will act on what you write, so every finding needs a concrete fix.

**Conditions.** Timer on, 45 minutes. No hints, no solutions, no AI assistance. Do not open
`checks_challenge/`: like an interviewer's answer sheet it names what a strong review covers.
Use the structure of section 2 of the lesson (requirements, data and labels, evaluation, serving,
monitoring, iteration) as your checklist, and use your `estimates.py` for any arithmetic.

**Acceptance criteria** (`python wb.py check w8d3 --challenge` verifies the structural ones).
1. At least six findings, each with a section reference that exists in the doc (`§1`-`§9`), a severity
   from {blocker, major, minor} and a fix of at least eight words.
2. At least two findings are blockers, and you can defend each blocker in one sentence: why would
   building it as written produce a wrong or unsafe system?
3. The evaluation, the label and the serving arithmetic are all reviewed (the checks look for the
   sections, not your wording).
4. A verdict other than plain approval if you found any blocker, and a summary of at most 120 words.
5. Scored against the rubric in `solutions/lessons/w8d3_system_design/challenge/RUBRIC.md` **after**
   you have finished: prioritisation and quality of fixes matter more than the number of findings.
