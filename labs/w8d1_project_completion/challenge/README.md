# Challenge: a gap list and a scoping memo (independent)

You have audited your project (lab) and now know what is missing, partial or not reproducible. With a
fixed amount of time left before you show the project to anyone, decide what to fix, what to defer and
what to drop **explicitly**, and write it down in [SCOPING_MEMO.md](SCOPING_MEMO.md).

A half-finished deliverable that is not mentioned reads as a mistake. The same gap, listed with its
impact and a reason it was scoped out, reads as judgement. Interviewers probe exactly this.

**Inputs.** Your `audit/REPRODUCTION_LOG.md`, your `DELIVERABLES.md`, the limitations recorded in your
milestone reports, and an honest estimate of the hours you have (the course assumes two sessions: w8d1
and w8d2, so 4-6 h, minus the time the report will take).

**Acceptance criteria** (`python wb.py check w8d1 --challenge`, structure only):
* the header states the hours available as a number;
* at least four gaps, each with evidence (a file, a log line, a number), the impact if left, an effort
  estimate in hours, a decision (`fix now`, `defer` or `scope out`) and a reason of six or more words;
* at least one gap is deferred or scoped out, and the `fix now` efforts add up to no more than the hours
  available;
* the section on what you will say about scoped-out items has at least 40 words;
* no placeholders left.

Quality is judged with the rubric in [../assessment.md](../assessment.md): are the gaps the ones that
matter, are the efforts realistic, does each scoped-out item come with what a reviewer should conclude?
