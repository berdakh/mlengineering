# Hint 2 — approach

1. Run `python wb.py check w7d6` and read the first failing check's message; then open the matching part
   of `src/flowguard/demo.py`:
   * versions and servers → the `if kind in ("promote", "rollback"):` block in `run_demo`;
   * summary mismatch → the Summary table in `render_report`, and the module constants at the top.
2. The reference structure of the block: switch the pointer (promote *or* rollback), then for both
   kinds: stop the current service, start a new one from `registry.path()`, record its pid.
3. Delete the constant the report uses and render every summary value from `results["summary"]`.
4. Runbook: start from `configs/alerts.toml`. Copy each `condition` into the Meaning line and add what is
   true when it fires; write First actions as numbered commands from the "Dashboards and queries" table.
