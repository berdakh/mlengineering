# w6d6 challenge: a blameless postmortem

**Time:** 30-40 minutes, unassisted. Read [`given/INCIDENT_TIMELINE.md`](given/INCIDENT_TIMELINE.md):
an incident in a *different* service (a demand forecaster) whose release passed every check and still
produced wrong predictions for 47 minutes. Write the postmortem in `challenge/POSTMORTEM.md` (the
starter has the headings).

This incident is the mirror image of the lab's: there, the service was visibly broken (503, OOM);
here, it was healthy by every operational signal and wrong. Your postmortem should make clear why the
existing checks could not catch it, and what would.

## Acceptance criteria

`python wb.py check w6d6 --challenge` checks structure, facts and tone; the rubric in
`solutions/labs/w6d6_cd_ops_debugging/assessment_answers.md` judges the reasoning:

* every heading of the starter is present and filled in (no TODO);
* **Impact** states the duration of customer impact in minutes, measured from when production started
  serving the release to when the rollback completed, and quantifies the business effect with the
  numbers from the timeline;
* **Timeline** has at least eight entries, uses only times that appear in the given timeline, and
  includes the start and the end of impact;
* **Action items** is a table with columns Action, Type, Owner, Due and at least four rows; Type is
  one of prevent, detect, mitigate, process; at least one item detects and one prevents; every item has
  an owner (a role or team is fine) and a due date;
* blameless language: no "human error", "should have", "careless", "blame", "fault", "negligent",
  and no person is named in **Root cause** or **Contributing factors**. Describe the system and the
  conditions that made the mistake possible and invisible, not who made it.
