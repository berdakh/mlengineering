# Debugging log: production incidents in the w6d6 lab

REFERENCE (w6d6). The evidence below is real output from the authoring run of 2026-11-22
(`solutions/lessons/w6d6_cd_ops_debugging/record/record_incidents.py`); your timestamps, digests and
the hotfix release id will differ. The order follows the recording (scenario 2, then 1, then 3).

## Incident 1

**Symptom:** Right after a hand-promoted "threshold hotfix" reached production, `fgops.py status`
showed production running and `health=unhealthy`, and `/readyz` answered 503. The deployment history
had recorded the same release as `failed` in staging sixteen seconds earlier.

**Evidence:**

```
$ python ops/fgops.py history production | tail -2
... production  b7c8d9e0f1a2   sha256:224d357c2a62...  good        promoted from staging
... production  6c7f7b608ec9   sha256:1b20cea7e16d...  failed      threshold hotfix (urgent, promoted by hand)
$ docker logs fgops-production 2>&1 | grep -v uvicorn.access
{"ts": "2026-11-22T17:29:53.938+00:00", "level": "ERROR", "logger": "flowguard.api", "msg": "model not loaded: /models/flowguard-z/1.0.0: checksum mismatch for model.json", "env": "production", "release": "6c7f7b608ec9", "event": "model_not_loaded"}
```

**Hypotheses:** (1) The new image contains a model bundle whose files do not match `checksums.json`
(edited after the bundle was built); (2) the model directory variable is wrong for this release;
(3) a transient file-system problem in the container.

**Test:** The log names the cause directly: `checksum mismatch for model.json` at
`/models/flowguard-z/1.0.0`, the configured path, so (2) is out. The same release failed the same way
in staging, so (3) is out. The note "threshold hotfix" plus the mismatch on `model.json` points to a
hand edit of the threshold without rebuilding the bundle.

**Root cause:** A release was built from a tree where `model.json` had been edited by hand (threshold
changed) without regenerating `checksums.json`; the bundle loader correctly refused it. It reached
production because it was promoted by hand although staging had recorded it as `failed`.

**Fix:** Rollback: `python ops/rollback.py production --apply` redeployed the previous good image,
release `b7c8d9e0f1a2`, by digest `sha256:224d357c2a62...`. A rollback is the right fix here because the
change that broke production was the image.

**Verification:** History: `production b7c8d9e0f1a2 ... good  rollback from 6c7f7b608ec9`; the polled
`/readyz` returned 200 again (figure 2 of the lesson); `status` showed `health=healthy`.

**Prevention:** Promotion only through `fgops.py promote`, which refuses anything not `good` in
staging; threshold changes go through the bundle builder (w5d2), which regenerates checksums; a CI
check that loads every bundle in the image before it is pushed.

## Incident 2

**Symptom:** After a configuration change to production (same image as before), `/readyz` returned
503 and the deployment was recorded as `failed`; `/healthz` still answered 200.

**Evidence:**

```
$ docker logs fgops-production 2>&1 | grep -v uvicorn.access
{"ts": "2026-11-22T17:30:20.518+00:00", "level": "INFO", "logger": "flowguard.serve", "msg": "starting flowguard 0.6.1", "env": "production", "release": "b7c8d9e0f1a2", "event": "starting", "model_dir": "/models/flowguard-z/1.0.1", "port": 8000}
{"ts": "2026-11-22T17:30:20.609+00:00", "level": "ERROR", "logger": "flowguard.api", "msg": "model not loaded: model directory not found: /models/flowguard-z/1.0.1", "env": "production", "release": "b7c8d9e0f1a2", "event": "model_not_loaded"}
$ grep MODEL_DIR ops/env/production.env
FLOWGUARD_MODEL_DIR=/models/flowguard-z/1.0.1
```

**Hypotheses:** (1) The environment points the service at a model version the image does not contain;
(2) the image is broken (as in incident 1); (3) a permission problem on /models.

**Test:** The release in the log is `b7c8d9e0f1a2`, the image that was healthy minutes earlier, so (2)
is unlikely. The `starting` line shows `model_dir: /models/flowguard-z/1.0.1`, and the image ships only
`1.0.0`; the error is "directory not found", not "permission denied", so (3) is out.

**Root cause:** `FLOWGUARD_MODEL_DIR` in `ops/env/production.env` was changed to `1.0.1`, a model
version that exists in no image. The setting passed format validation (an absolute path), and the
service correctly started but stayed not-ready.

**Fix:** Revert the variable (`fgops.py reset`) and redeploy the **same digest**. Not a rollback:
`rollback.py` would have picked release `a1b2c3d4e5f6`, an older image, which would also fail with this
environment file and would undo a good release.

**Verification:** History `production b7c8d9e0f1a2 ... good  revert MODEL_DIR`; `/readyz` 200.

**Prevention:** Keep the model version and its directory in the image (one image = one model) and
derive the path from the bundle's own metadata, or check at deploy time that the configured directory
exists in the image (`docker run --rm <digest> ls <dir>`) before replacing the running container.

## Incident 3

**Symptom:** After a "right-size memory" change, production answered `/readyz` with 200 for a few
seconds, then stopped answering; `status` showed the container `exited`, and the deployment was
recorded as `failed`.

**Evidence:**

```
$ docker inspect -f '{{.State.Status}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}}' fgops-production
exited oom=true exit=137
$ docker logs fgops-production 2>&1 | grep -v uvicorn.access | tail -2
{"ts": "2026-11-22T17:30:47.695+00:00", "level": "INFO", "logger": "uvicorn.error", "msg": "Application startup complete.", "env": "production", "release": "b7c8d9e0f1a2"}
{"ts": "2026-11-22T17:30:47.696+00:00", "level": "INFO", "logger": "uvicorn.error", "msg": "Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)", "env": "production", "release": "b7c8d9e0f1a2"}
$ grep -A4 '"production"' ops/env/runtime.json
  "production": {
    "port": 8102,
    "memory": "64m",
    "cpus": "0.5"
  }
```

**Hypotheses:** (1) The kernel killed the container for exceeding its memory limit; (2) the
application crashed (an exception would be logged); (3) the health check killed it.

**Test:** The logs end on a normal startup line with no ERROR and no traceback, which argues against
(2); `docker inspect` shows `OOMKilled=true` and exit code 137 (128 + SIGKILL 9), which confirms (1).
Docker does not stop containers for failing health checks, so (3) is out. The service uses about
64 MiB at idle (measured with `docker stats` under a 96 MiB limit), so a 64 MiB limit leaves no room
for the second Python process the health check starts.

**Root cause:** The production memory limit in `ops/env/runtime.json` was lowered from 256m to 64m,
below the service's working set.

**Fix:** Restore 256m and redeploy the same digest. Again not a rollback: the image was fine.

**Verification:** History `production b7c8d9e0f1a2 ... good  revert memory`; the container stayed up
and healthy, `OOMKilled=false`.

**Prevention:** Size limits from measurement (peak memory under a load test, w6d4) with headroom;
alert on container restarts and OOM kills; let a deployment count as good only after the container
has stayed healthy for longer than one health-check cycle, not at the first 200.
