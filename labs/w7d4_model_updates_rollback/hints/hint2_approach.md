# Hint 2 (approach)

* **Task 2.** `diff = paired_bootstrap_diff(pooled_recall, candidate, current, n_boot=..., seed=..., level=...)`
  gives `estimate`, `low`, `high` for candidate minus current. Primary check by policy; guardrail with
  `pooled_far(candidate.values())`; for slices, group experiment ids by slice name and compare pooled
  recalls with `slice_margin`. Collect a human-readable reason for every failed check.
* **Task 3.** In `score`: `response = respond(self.current, run)` first; then
  `try: respond(self.candidate, run.copy(deep=True))` inside `except Exception`. In `disagreements`,
  an alarm `[s, e)` overlaps another `[s2, e2)` when `s < e2 and s2 < e`.
* **Task 4.** `_check_deployable(root, name, version, serving_columns)`: `list_versions`, `load_bundle`,
  then compare `doc["input_schema"]["required"]` with `serving_columns`. A shared `_move(...)` helper that
  reads `current_version`, calls `write_pointer`, then appends the audit line serves both promote and rollback.
* **Task 5.** Replay `audit_log`: `promote` pushes the entry, `rollback` pops. The target is the `from` of
  the top entry; None means there is nothing older to return to.
