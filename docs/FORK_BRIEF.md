# Brief for authoring one unit (read with docs/AUTHORING.md and docs/FLOWGUARD_SPEC.md)

Model your unit on the finished ones: `lessons/w1d3_package_structure/`, `lessons/w1d4_config_logging/`,
`lessons/w1d5_testing_ml_code/` and their `solutions/lessons/...` trees. Same layout, same depth.

Scope rules
* Write only inside your unit's `lessons/<id>/`, `solutions/lessons/<id>/` and the handbook file(s) named
  in your task. Never edit README, STATUS, ROADMAP, course.json, tools/, docs/, data/, other units.
* No git commands that change state. Clean `__pycache__`, `*.egg-info`, venvs and run outputs when done.
* Dependencies: stdlib, numpy, pandas, scikit-learn, scipy, pydantic, pytest unless your task names more.
  If you need another package, install it, and report it so requirements can be updated.

Lesson content (README.md, all eight sections): 1 Purpose (objective, why, prerequisites, time budget:
2 h essential + optional extension <= 1 h); 2 Conceptual explanation (intuition, precise terms, maths and
assumptions, link to the learner's EEG/iEEG research background, a concrete industry example, limits and
misconceptions); 3 Worked example (complete runnable code in `example/`, data schema, key decisions,
real output copied from a run, interpretation, how to reproduce); 4 Guided lab (sequential tasks, starter in
`lab/`, checkpoints, debugging guidance); 5 Independent challenge (transfer, acceptance criteria, no
solution); 6 Progressive hints (links to hints/hint1_concept.md, hint2_approach.md, hint3_partial.md);
7 Assessment (link to assessment.md: reasoning questions, >= 1 design-choice explanation, rubric, one
10-15 min "interview rep" from the strand named in your task); 8 Reflection (what you can now do alone,
reflection prompt, a later retrieval question, link to the next unit).
The learner is an experienced ML researcher (PyTorch, EEG/iEEG time series, cross-subject evaluation)
moving to industry. Do not explain basics. No padding, no API catalogues.

Checks: pytest, target via `tools.wbcheck.resolve_target("<unit path>", "<part>")`; behaviour and
contracts, not one implementation; offline, deterministic, fast (< 30 s per suite); never require downloaded
data. Solutions: `lab/`, `challenge/`, `mutants/`, `mutants_challenge/` (2-4 plausible wrong submissions
each with MUTANT.md), `assessment_answers.md` (model answers, common incorrect answers and why they fail).

Handbook section(s): original textbook-quality prose with stable id heading (e.g. `# H3.1 ...`): overview,
deeper explanation with examples, relevant equations, practical decisions and tradeoffs, common failure
modes, quick reference, sources and verification status (list pages actually opened; flag anything from
memory). Rendered doc sites are often blocked here; read doc sources from raw.githubusercontent.com.

Honesty: copy numbers only from runs you made. Synthetic data is labelled SYNTHETIC with what it cannot
show. Real-data results are reported as found, including unimpressive ones. Never invent citations.

Verify before reporting: run the example; run the reference solutions; `python tools/verify_checks.py
lessons/<id>` passes for both parts with every mutant rejected; the shipped starter fails its checks.

Report (<= 250 words): files written; commands run with real outcomes; sources opened; anything
unverified; new dependencies; anything the integrator must act on.
