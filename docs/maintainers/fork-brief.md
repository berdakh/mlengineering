---
title: "Unit authoring brief"
parent: Maintainers
nav_order: 2
---

# Brief for authoring one unit (read with docs/maintainers/authoring.md and docs/maintainers/flowguard-spec.md)

Model your unit on the finished ones: `labs/w1d3_package_structure/`, `labs/w1d4_config_logging/`,
`labs/w1d5_testing_ml_code/` and their `solutions/lessons/...` trees. Same layout, same depth.

Scope rules
* Write only inside your unit's `labs/<id>/`, `solutions/labs/<id>/` and the handbook file(s) named
  in your task. Never edit README, STATUS, ROADMAP, course.json, tools/, docs/, data/, other units.
* No git commands that change state. Clean `__pycache__`, `*.egg-info`, venvs and run outputs when done.
* Dependencies: stdlib, numpy, pandas, scikit-learn, scipy, pydantic, pytest unless your task names more.
  If you need another package, install it, and report it so requirements can be updated.

Lesson content (README.md, all eight sections): 1 Purpose (objective, why, prerequisites, time budget:
2 h essential + optional extension <= 1 h); 2 Conceptual explanation (intuition, precise terms, maths and
assumptions, connection to other domains, a concrete industry example, limits and
misconceptions); 3 Worked example (complete runnable code in `example/`, data schema, key decisions,
real output copied from a run, interpretation, how to reproduce); 4 Guided lab (sequential tasks, starter in
`lab/`, checkpoints, debugging guidance); 5 Independent challenge (transfer, acceptance criteria, no
solution); 6 Progressive hints (links to hints/hint1_concept.md, hint2_approach.md, hint3_partial.md);
7 Assessment (link to assessment.md: reasoning questions, >= 1 design-choice explanation, rubric, one
10-15 min "interview rep" from the strand named in your task); 8 Reflection (what you can now do alone,
reflection prompt, a later retrieval question, link to the next unit).
The audience is students who can already write Python and train a basic model, and who are learning to
deliver models as reliable software. Explain new ideas properly; do not re-teach Python basics. No padding,
no API catalogues.

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
labs/<id>` passes for both parts with every mutant rejected; the shipped starter fails its checks.

Report (<= 250 words): files written; commands run with real outcomes; sources opened; anything
unverified; new dependencies; anything the integrator must act on.

## Visuals (required in every lesson and handbook section)

The learner asked for more visuals. Each lesson needs at least four, each handbook section at least two,
placed where they carry an idea better than prose. Two kinds:

1. **Diagrams as Mermaid** in fenced ```mermaid blocks (GitHub renders them): pipelines and data flow,
   package/module structure, decision trees, sequence diagrams (request -> validation -> model -> response),
   state machines, timelines of train/validation/test splits (`gantt` works well for split layouts).
   Keep each under ~15 nodes; label edges; no styling directives beyond defaults. For layouts Mermaid
   draws badly (e.g. fold-by-experiment grids), use a small ASCII/Unicode block diagram in a code fence.
2. **Data figures from real runs**: a committed script `figures/make_figures.py` in the unit (or
   `handbook/figures/<section>/make_figures.py`) that imports `tools.figstyle` (read its docstring and
   obey its rules), regenerates every figure deterministically, and writes `figures/*.svg`. Embed with
   X followed by a one-sentence caption that
   says what to look at and whether the data is SYNTHETIC or real. Numbers in a figure must come from
   a run of that script; print them too so the lesson's table matches. Typical candidates: a signal with
   the labelled event and the detector's alarms; causal vs centred window response to a step; score
   distributions by class; PR and ROC curves side by side; a reliability curve; interval plots
   (point estimate + CI per model); leaky vs honest estimates; latency histograms with percentiles.
   Small multiples instead of dual axes. matplotlib is a figure-authoring dependency only: labs and
   checks must not import it.

Before finishing, open each SVG's rendering once (convert to PNG with matplotlib and view it with the
Read tool) to catch overlapping labels or empty plots. Report the list of figures.
