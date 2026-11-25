---
title: "Interview practice"
parent: Guides
nav_order: 9
---

# Interview practice: short, recurring, with fading assistance

Status: all seven sets are written; every coding prompt's reference answer was executed against its tests
and plausible wrong answers are rejected. Every lesson also ends with one short "interview rep" in its `assessment.md`.

| Set | Review day | Focus |
|---|---|---|
| [1](../../interview/set1_python_structure.md) | w1d7 | Python coding, project structure |
| [2](../../interview/set2_sql_pandas.md) | w2d7 | SQL and pandas (`python interview/set2_check.py`) |
| [3](../../interview/set3_validation_fundamentals.md) | w3d7 | Validation, leakage, ML fundamentals (spoken) |
| [4](../../interview/set4_explain_evaluation.md) | w4d7 | Explaining your evaluation in 5 minutes |
| [5](../../interview/set5_system_design.md) | w5d7 | ML system design rep 1 + API contract coding |
| [6](../../interview/set6_debugging.md) | w6d7 | Debugging narratives + log-analysis coding |
| [7](../../interview/set7_system_design.md) | w7d7 | ML system design rep 2 (operating a model) + retry coding |

Week 8 adds full timed sessions: [system design](../../labs/w8d3_system_design/README.md),
[coding and SQL](../../labs/w8d4_coding_interviews/README.md) and
[project explanation](../../labs/w8d5_project_explanation/README.md). Rubrics and worked answers are in
`solutions/interview/`; attempt first.

## Cadence

* **Core days:** one 10-15 minute rep at the end of the session, rotating through the strands below.
* **Review day (day 7):** one 30-45 minute mixed, timed set.
* **Week 8:** full-length timed sessions (w8d3-w8d5).

| Strand | What a rep looks like | Rotation |
|---|---|---|
| Python coding and data structures | one function, stated complexity, tests you write yourself | days 1, 4 |
| SQL | one query against a small schema; state the grain of the result | day 2 |
| ML fundamentals | explain-and-derive question (e.g. why L2 shrinks correlated coefficients together) | day 3 |
| Validation and leakage | spot the flaw in a described experiment and propose the fix | day 4 |
| Debugging | a failing snippet or a suspicious metric; narrate your hypothesis ordering | day 5 |
| System design / project explanation | 10-minute slice of a design, or a 2-minute project answer | day 6 |

## Fading assistance

| Weeks | Conditions |
|---|---|
| 1-2 | Untimed first attempt; rubric and worked answer available afterwards |
| 3-5 | Timed; rubric only (no worked answer) until you have written a second attempt |
| 6-8 | Timed and spoken aloud or recorded; self-score against the rubric before reading any answer |

## Rules that make the practice honest

1. Write or say the answer before opening any rubric. A rep read but not attempted is logged as "read".
2. Log each rep in `progress/notes.md` with: strand, time, what went wrong, the pattern behind the error.
3. Level: prompts target mid-level Machine Learning Engineer / Applied Scientist loops. An academic title
   does not imply a senior engineering target; seniority expectations are discussed in w8d3 with evidence
   from your own system-design reps.
