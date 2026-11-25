# Hint 3 (partial implementation)

```python
def offline_gate(current, candidate, *, policy="superiority", margin=0.05, max_false_alarms_per_hour=None,
                 slices=None, slice_margin=0.0, n_boot=2000, seed=0, level=0.95):
    if policy not in POLICIES:
        raise ValueError(...)
    if set(current) != set(candidate):
        raise ValueError(...)
    diff = paired_bootstrap_diff(pooled_recall, candidate, current, n_boot=n_boot, seed=seed, level=level)
    checks = {"superior": diff["low"] > 0, "non_inferior": diff["low"] > -margin}
    primary = checks["superior"] if policy == "superiority" else checks["non_inferior"]
    # TODO guardrail, slices, reasons, decision


class ShadowRunner:
    def __init__(self, current, candidate, log=None):
        self.current, self.candidate = current, candidate
        self.log = [] if log is None else log

    def score(self, run_id, run):
        response = respond(self.current, run)
        record = {...}
        try:
            record["candidate_alarms"] = respond(self.candidate, run.copy(deep=True))["alarm_events"]
        except Exception as exc:
            record["candidate_error"] = f"{type(exc).__name__}: {exc}"
        self.log.append(record)
        return response


def _move(root, name, action, version, actor, reason):
    previous = current_version(root, name)
    write_pointer(root, name, version)          # atomic; raises before anything is written to the audit
    # TODO append one JSON line to <root>/<name>/audit.jsonl
```
