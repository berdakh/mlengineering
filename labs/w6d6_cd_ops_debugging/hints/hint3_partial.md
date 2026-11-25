# w6d6 hint 3: partial implementation

`settings.py` (the first half; the remaining checks follow the same pattern):

```python
def _required(env, name):
    value = env.get(name, "").strip()
    if not value:
        raise SettingsError(f"{name} is required but not set")
    return value


def load_settings(env):
    unknown = sorted(k for k in env if k.startswith(PREFIX) and k not in KNOWN)
    if unknown:
        raise SettingsError(f"unknown variable(s) {', '.join(unknown)}; expected only {', '.join(KNOWN)}")
    environment = _required(env, "FLOWGUARD_ENV")
    if environment not in ENVIRONMENTS:
        raise SettingsError(f"FLOWGUARD_ENV must be one of {', '.join(ENVIRONMENTS)}, got {environment!r}")
    model_dir = _required(env, "FLOWGUARD_MODEL_DIR")
    if not model_dir.startswith("/"):
        raise SettingsError(f"FLOWGUARD_MODEL_DIR must be an absolute path, got {model_dir!r}")
    ...  # FLOWGUARD_RELEASE, FLOWGUARD_LOG_LEVEL (default INFO), FLOWGUARD_PORT (default 8000)
    return Settings(environment=environment, model_dir=model_dir, release=release,
                    log_level=log_level, port=port)
```

`rollback.py`:

```python
def select_rollback_target(history, env):
    entries = sorted((e for e in history if e.get("env") == env), key=lambda e: e["deployed_at"])
    if not entries:
        raise RollbackError(f"{env} has no deployments")
    current = entries[-1]
    for entry in reversed(entries[:-1]):
        ...   # good, and a different digest from current
    raise RollbackError(...)
```

**Incident triage, the three questions that separate them:**

| Question | How to answer it |
|---|---|
| Did the image change? | `history production`: compare the current digest with the previous good one |
| What did the process report at startup? | `docker logs fgops-production 2>&1 \| grep -v uvicorn.access \| head` |
| Is the process still alive, and if not, why? | `docker inspect -f '{{.State.Status}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}}' fgops-production` |
