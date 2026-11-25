# w6d6 hint 1: the concept

* **Settings.** Validate *names* first (an unknown `FLOWGUARD_*` variable is a typo until proven
  otherwise), then each value's *format*. Do not check whether the model directory exists: that is the
  readiness probe's job, and the container should keep running and logging when it is not ready.
* **Rollback target.** "Current" is a fact about time, not about list position: the latest
  `deployed_at` for that environment. The target is the newest *earlier* entry that was `good` *and* runs
  a different image. If the image that is running now was good before, a rollback to it changes nothing:
  that situation is a configuration incident.
* **Digest, not tag.** A rollback deploys exactly what ran before. Only a digest says that.
* **Incidents.** Each of the three has one change behind it. Find the change first (history, the startup
  log line, `git diff -- ops/env`), then decide whether the change was the image or the configuration.
  Logs tell you what the process saw; `docker inspect` tells you what happened to the process.
