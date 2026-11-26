---
title: "Interview practice"
parent: Guides
nav_order: 8
---

# Interview practice

Interviews for ML engineering roles vary a lot between companies and levels. Practice makes you calmer and
clearer; it does not guarantee an outcome, and this course makes no promise about one.

## In the 12-week course

[Notebook 47 · Interview preparation](../notebooks/47_interview_preparation.html) (Week 12) covers the five
common strands, with graded practice where a grader can judge the answer:

| Strand | What you practise | Built on |
|---|---|---|
| SQL | Timed problems on the shop database, graded like Weeks 2-3 | Notebooks 05-09 |
| Python | Small coding problems with tests | Notebooks 02, 30 |
| ML concepts | Leakage, metrics, validation, bias and variance, with explanations | Notebooks 17-27 |
| ML system design | A structured framework, a worked example, a design exercise | Weeks 9-11 |
| Behavioural | Telling a project story with the STAR structure | Notebook 46 |

Habits that help, whichever strand:

1. **Attempt before you read.** Write or say your answer, then check. A question you only read is not practice.
2. **Say your reasoning aloud**, including what you would check next. Interviewers grade the reasoning.
3. **Keep a log** in `progress/notes.md` (or `note("47", "...")`): the question, your time, what went wrong, and
   the pattern behind the error.
4. **Use your project.** "I found that elapsed time predicted the label, so I removed position features" is a
   stronger answer than any definition.

## More sets in the advanced track

The advanced track has seven timed sets with rubrics and worked answers (attempt first; answers are in
`solutions/interview/`):

| Set | Focus |
|---|---|
| [1](../../interview/set1_python_structure.md) | Python coding, project structure |
| [2](../../interview/set2_sql_pandas.md) | SQL and pandas (`python interview/set2_check.py`) |
| [3](../../interview/set3_validation_fundamentals.md) | Validation, leakage, ML fundamentals (spoken) |
| [4](../../interview/set4_explain_evaluation.md) | Explaining your evaluation in 5 minutes |
| [5](../../interview/set5_system_design.md) | ML system design + API contract coding |
| [6](../../interview/set6_debugging.md) | Debugging narratives + log-analysis coding |
| [7](../../interview/set7_system_design.md) | ML system design: operating a model + retry coding |

Full timed sessions are in advanced sessions
[w8d3 (system design)](../../labs/w8d3_system_design/README.md),
[w8d4 (coding and SQL)](../../labs/w8d4_coding_interviews/README.md) and
[w8d5 (project explanation)](../../labs/w8d5_project_explanation/README.md).
