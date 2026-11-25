# Hint 1 - the one question

Ask of every **column**, every **row** and every **fitted or chosen step**:

> Would this exist, in this form, at the moment the prediction is made?

* Column: *when is this field written, and by which system?* A field written by the collections team
  after the due date does not exist at issue time. An aggregate stored in an export was computed when
  the export was taken.
* Row: *is this the same event as another row?* and *could this row's twin be on the other side of the
  split?* Copies, re-issues and overlapping recordings are one event, so they belong on one side.
* Step: *which rows did this statistic, selection or choice see?* If the answer includes rows you
  evaluate on, the evaluation is no longer of the procedure you will deploy.

For SKAB the same question gives the two project leaks: duplicated rows across files (row question) and
elapsed time (column question: `t` exists at prediction time, but its relationship to the label is a
property of how the experiments were run, not of pumps).
