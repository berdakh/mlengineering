# Drift report: the service that passed two weeks ago fails today - REFERENCE ANSWER

## What changed

Nothing in our repository. `./build.sh` resolves `service/requirements.in` (`zscorelib>=1.0`) at build
time. Two weeks ago the newest matching release in the index was zscorelib 1.0.0, the expected scores
were recorded with it, and the smoke test passed. Today the index also holds 1.1.0, so the same build
installs 1.1.0 (`installed: zscorelib-1.1.0.dist-info`) and the smoke test fails. Every score after the
burn-in differs, although the code, the input and the expected file are byte-identical.

## Why the build drifted

`>=1.0` is a range, so the result of the build depends on the date it runs. 1.1.0 is a minor release
and therefore accepted by the range, but it changed behaviour: `calibrate` now divides by n - 1
(sample standard deviation) instead of n. With a 20-sample burn-in the SD grows by sqrt(20/19), about
2.6 %, so every z-score shrinks by the same factor and threshold decisions near the boundary flip.
Semantic versioning is a promise from the publisher, not a guarantee: changing a statistical
definition in a minor release is exactly the kind of change a smoke test exists to catch.

## Fix

`service/requirements.lock` pins the version that was validated, `zscorelib==1.0.0`, with the sha256
of the 1.0.0 wheel, and `build.sh` installs it with `--require-hashes -r service/requirements.lock`.
In hash-checking mode pip installs exactly that file or nothing. Verified: `./build.sh` installs
zscorelib 1.0.0 and the smoke test passes; editing the lock to 1.1.0 with its hash makes the smoke
test fail again, and leaving out the hash makes pip refuse to install. Note that compiling the lock
today (`uv pip compile`) would pick 1.1.0: the lock must record what was tested, not what is newest.

## Prevention

Build only from the lock (CI fails if requirements.in changes without a recompiled lock). Upgrade
deliberately: recompile, rebuild, run the smoke test and the evaluation (here 1.1.0 would also change
the detector's operating point, which was chosen with the population SD), review the diff of the lock
in the pull request, then record the new expected scores. Pin the base image by digest for the same
reason. Keep the smoke test in CI so that the next silent change fails a build instead of a deployment.
