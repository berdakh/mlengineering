# Challenge: peer-review a flawed report (independent)

[FLAWED_REPORT.md](FLAWED_REPORT.md) is a short SYNTHETIC report on late-payment prediction, written for a
finance team. Review it as a sceptical colleague: find what is wrong, explain why it matters, and request a
concrete change. Write the review in [REVIEW.md](REVIEW.md). Time box: 40 minutes, no hints.

This is the other side of today's lab: the rules your checker enforces catch some problems mechanically;
most of the serious ones in this report need judgement.

**Acceptance criteria** (`python wb.py check w8d2 --challenge`, structure plus coverage):
* at least six issues, each with a line number in `FLAWED_REPORT.md`, a problem, why it matters, a requested
  change of six or more words, and a severity (`major` or `minor`); at least three are `major`;
* the issues point at (by line number) at least five of the problems the report was written to contain;
* the summary and recommendation sections are written; no placeholders left.

The model answer, with every planted problem explained, is in the solutions folder.
