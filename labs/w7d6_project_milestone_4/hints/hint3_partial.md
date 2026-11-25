# Hint 3 — partial implementation

```python
# demo.py, inside the event loop of run_demo
if kind in ("promote", "rollback"):
    if kind == "promote":
        registry.promote(bad.model_version if ev["version"] == "bad" else good.model_version,
                         ev.get("reason", ""))
    else:
        registry.rollback(ev.get("reason", ""))
    service.stop()
    service = Service(registry.path(), settings_path, log_file, src_dir)
    pids.append(service.proc.pid)
```

```python
# demo.py, render_report: the Summary table comes from results only
lines += [f"| {k} | {_fmt(v)} |" for k, v in results["summary"].items()]
```

One runbook entry, as a shape to copy (fill in your own commands and numbers):

```markdown
### InputOutOfSupport

**Meaning:** values outside the range seen in development data (...). Scores for them are extrapolation;
the z-score is scale invariant, so a units error does not change alarms.
**First actions:** 1) find the machine in `predict` log events with `out_of_support > 0`; 2) ...; 3) ...
**Escalate:** gateway team the same day (SEV2); ...
```
