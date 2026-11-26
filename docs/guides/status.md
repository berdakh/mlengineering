---
title: "Status and verification"
parent: Guides
nav_order: 10
---

# Status and verification
{: .no_toc }

Last updated: 2026-11-26. Nothing here records a learner's result; each student's own record lives in
`progress/`.

1. TOC
{:toc}

---

## The 12-week course

The course was rebuilt from scratch for students with intro-ML theory and no industry tools: 12 weeks, 48
notebooks, graded inside the notebook, Colab first. See [how it is designed](program-design.html).

| Weeks | State |
|---|---|
| 1-12 | Written and verified (below): 427 graded exercises and 228 quiz questions in 48 notebooks |

### What is verified

* **Every exercise is gradable, and no starter passes.** `python tools/verify_notebooks.py` executes both copies of
  each notebook with a Jupyter kernel: the solved copy (`solutions/notebooks/`) must pass every grader with no cell
  errors, and the student copy (`notebooks/`) must fail every grader, raising nothing but `NotImplementedError`.
  All 48 notebooks pass.
* **Graders reject typical mistakes.** While writing each week, its author fed the graders plausible wrong answers
  (off-by-one boundaries, counting cancelled orders, random folds where grouped folds were needed, leaky
  scores, tests that miss a planted bug) and checked that each was rejected with a message that does not give the
  answer away. These were spot checks, not an exhaustive suite.
* **Notebooks are well-formed.** `python tools/check_notebooks.py`: valid JSON, code parses, links and images exist,
  Colab badges point at the right file.
* **Numbers are real.** Every number quoted in a lesson comes from running its code on the course's synthetic data
  or on SKAB.

### What is not verified yet

1. **No student has taken the course.** Time estimates (75-120 minutes a lesson, 6-8 hours a week) are the authors'
   estimates, not measurements, and no lesson has been tested on a learner.
2. **Colab runs are not automated.** Notebooks are executed with a local Jupyter kernel on Linux with Python 3.13.
   The setup cell is written for Colab and Colab's installed packages; a change on Colab's side can break it.
3. **Weeks 10-11 local steps.** Installing VS Code, Python, Git and Docker on each operating system is written
   from the official documentation and was not tried on each system. Docker images in Week 10 were built and run
   on Linux, and the quoted outputs come from those runs. The example GitHub Actions workflows passed `actionlint`
   and their commands passed locally, but the workflows were not run on GitHub. The AWS commands in Week 11 were
   never run (no cloud resources were created), and the prices in its examples are invented for practice.
4. **The site** is built by GitHub Pages from `docs/`. A local Jekyll build is used to check it, but the published
   site could not be opened from the authoring environment.
5. **One authoring pass by AI authors, then independent re-verification.** Explanations have not had an
   independent human review. Report anything that looks wrong.
6. **Synthetic data.** The shop database and other course datasets are generated; they support conclusions about
   code and reasoning, not about any real business.
7. **Small evaluation sample in the project.** The frozen SKAB test set has 7 experiments, so many comparisons are
   honestly reported as "no detectable difference".

## The advanced track

The earlier 48-session program, now the [advanced track](../advanced/). Its facts below are unchanged from its last
full verification. Session ids (`w3d4`) and notebook numbers in this section refer to the
[advanced schedule](../advanced/schedule.html), not to the 12-week course.

| | Count |
|---|---|
| Sessions | 56: 48 core days (one notebook each) and 8 review days |
| Handbook sections | 55, in 16 chapters ([index](../handbook/index.md)), shared with the 12-week course |
| Interview sets | 7 ([practice guide](interview-practice.md)) |

### How it was verified

All of this was run on 2026-11-25, before the track moved under `advanced/` (paths below are as they were then):

* **Lab checks verify what they claim.** `python tools/verify_checks.py --all`: **104 reference solutions
  pass their checks and all 509 plausible wrong submissions are rejected.** The run found two failures caused by
  the restructure itself (a path rewrite had altered checksummed model bundles); both were fixed, and every
  lesson changed after its turn in that run (eight in all) was verified again in full, with no failures.
* **Starters fail.** Every shipped lab and challenge starter fails its checks, so passing means work was done.
* **Every notebook was executed from top to bottom** (Jupyter kernel, Python 3.13): 48 of 48 ran with **no
  cell errors**. Commands inside cells that print tracebacks were each classified: all come from checks run
  on unfinished starter code, lab scripts stopping at "implement task N" placeholders, or the one Docker demo
  that needs a running Docker daemon. The two less obvious ones (notebooks 37 and 41) were re-run against the
  reference lab and succeed.
* **The course site was built** with Jekyll 3.10 and the just-the-docs 0.10.1 theme (the versions GitHub Pages
  uses): 149 pages, no build errors. Pages were checked in a browser; every relative link resolves
  (`tools/check_links.py`), and every notebook passed `tools/check_notebooks.py` (valid JSON, code parses,
  links and images exist, Colab badges point at the right file).
* **Real-data results** come from runs on the SKAB files; from Week 3 on, all use the frozen split manifest
  `solutions/labs/w3d1_leakage/lab/splits/v2.json` (7 test, 27 development experiments).
* **Live infrastructure where it was available.** Docker images were built and run (Weeks 6-7); FastAPI
  services were run with uvicorn on 127.0.0.1 and stopped; a clean-clone reproduction audit rebuilt the
  milestone project and reproduced all 18 headline numbers exactly (notebook 43).
* **Prose.** Each handbook section ends with "sources and verification status": the documentation sources
  opened (usually source repositories on GitHub, because rendered documentation sites were blocked) and what
  was written from memory.

Tested versions are in [the maintainers' notes](../maintainers/tested-versions.md).

### Real findings it is built around

These came out of running the material on the real data; lessons report them as found.

* SKAB files share 1,290 duplicated rows, 235 with contradictory labels; the split is repaired in w3d1.
* Elapsed time predicts the label (anomaly onset at row 550-600 in 31 of 34 files); a "clock" baseline beats
  every sensor baseline in w2d6, so position-in-recording features are forbidden.
* Row-level cross-validation reports ROC-AUC 0.986 where experiment-level reports 0.849 (w2d4).
* Gradient-boosted trees win on the frozen test set but fall to the level of one z-score on an unseen fault
  family (w4d2); the neural autoencoder does not beat the classical detectors (w4d3); the model-choice rule
  ships a burn-in flow-rate z-score detector (w4d5).
* The input-drift monitor flags only 14-20 % of fault windows (w7d2); a sensor recalibration causes massive
  drift with no loss of detection, while a threshold regression cuts recall from 11/20 to 4/20 with no drift
  flag (w7d3).
* Operational surprises measured, not assumed: uvicorn with several workers added about 40 ms through Nagle's
  algorithm (w6d4); a multi-stage image was not smaller than a single-stage slim image (w6d2); pandas' default
  CSV float parser is not round-trip exact (w5d1).

### Known limitations

1. **One authoring pass per unit, by AI authors.** Every unit was written and checked against sources by
   its author, and some were corrected by a later consistency pass. None has had an independent human
   review. Treat explanations as carefully drafted, and report anything that looks wrong.
2. **Python versions.** Material was executed on Python 3.13. Python 3.11 and 3.12 were covered by CI for the
   checks verification of Weeks 1-3 only; Weeks 4-8 have not run on 3.11 or 3.12 (see "CI result").
3. **Not run on a student laptop.** The authoring environment is a Linux container. Distribution-specific statements (system
   Python 3.10, installing Docker Engine) are from documentation sources or memory and labelled. Some timing
   checks use Unix signals and would not work on Windows.
4. **Documentation access.** Rendered documentation sites (docs.python.org, AWS docs and pricing, RFC pages and
   others) were blocked. Official sources were read from their GitHub repositories where possible. External
   links in the text were not click-tested.
5. **Citations from memory** are labelled in each handbook section's sources part.
6. **Time boxes are estimates.** No one has yet sat the diagnostic or any lesson against the clock.
7. **AWS was never called.** The w6d5 deployment route (ECR + ECS Fargate, private by default) is checked
   against AWS CLI example sources and API models only. No prices are stated. One open discrepancy
   (`assignPublicIp`) is flagged in the lesson. Live mode requires your signed briefing and `--live`.
8. **Small evaluation sample.** SKAB has 34 labelled events and the frozen test set has 7 experiments, so many
   comparisons are honestly reported as inconclusive. SKAB is GPL-3.0 and is downloaded, not redistributed.
9. **Synthetic data** is used for Week 1 labs, the diagnostic, the final assessment, the transfer exercises
   and all checks. It supports conclusions about code and reasoning, not about real-world model quality.
   UCI Bank Marketing could not be reached to verify access and licence, so transfer uses synthetic business data.
10. **Project snapshots.** Each project lesson ships its own snapshot of upstream `flowguard` modules, written to
    [docs/maintainers/flowguard-spec.md](../maintainers/flowguard-spec.md); small differences exist between snapshots. Your own
    project repository is the single real implementation.
11. **Visibility of answers.** Solutions, scoring guidance and some grading fixtures are in the repository. The
    diagnostic and final assessment are only informative if you do not open them first.
12. **Week 3+ real-data numbers depend on the frozen v2 manifest.** Week 2 used v1 (9 test, 25 development);
    w3d1 explains the repair.

### Next steps

1. **Students:** start with advanced notebooks 01-02 (the diagnostic), then follow the [advanced weekly plan](../advanced/weeks/).
2. **Instructors:** review a student's diagnostic against `solutions/diagnostic/SCORING.md` and decide which
   Week 1-3 sessions they can compress; record outcomes in their `progress/SKILLS_LEDGER.md`.
3. **Maintenance:** edit `advanced/notebook_src/`, then rebuild with `python tools/nbbuild.py --src advanced/notebook_src --out advanced/notebooks --solutions ""`; after any change to a lab run
   `python tools/verify_checks.py labs/<session>`; keep `make check` and CI green.

### CI result (advanced-track history)

* Runs 1-24 (2026-11-21 to 2026-11-22) passed on Python 3.11, 3.12 and 3.13.
* From run 25 (2026-11-22 16:17 UTC) the CI jobs fail within about a second without being assigned a runner:
  no steps run and no logs exist, while the same verification passes locally. While the repository is private,
  the most likely cause is the account's GitHub Actions minutes or spending limit. **Public repositories get
  free Actions minutes**, so making the repository public should let CI and the site deployment run.
* The workflow now has a fast job (notebooks, site, links, course tests) on every push and the long lab
  verification as a separate job (one Python version on push, three weekly and on demand).
