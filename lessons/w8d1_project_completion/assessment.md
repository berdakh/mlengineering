# W8D1 assessment: completion audit

## Rubric (the reviewer uses this; you self-score in the memo)

| Criterion | 1 (below) | 2 (meets) | 3 (exceeds) |
|---|---|---|---|
| Reproduction | audit not run, or run on the working tree | audit log committed for the current commit; FAIL findings explained | PASS, plus a second Python version or machine |
| Environment | direct dependencies only, or `>=` | full lock from a clean venv | lock plus a container built from it (w6d2) and the same numbers inside |
| Headline coverage | one or two numbers | every number quoted in the report's summary | plus a repeat run showing determinism |
| Deliverables audit | statuses without evidence | evidence a reviewer can open for every `done` | partial items quantified (what exactly is missing) |
| Scoping | a wish list | decisions that fit the stated hours, reasons given | what each scoped-out item means for the claims, stated in the report |

## Reasoning questions

1. Your audit passes, but a colleague's identical clone on macOS gives a test PR-AUC that differs in the fourth
   decimal. Is that a reproducibility failure? What do you check first, and what tolerance would you then set,
   with what justification?
2. Why must the audit clone rather than copy, even if you are sure your working tree is clean?
3. The lock lists `numpy==2.5.3` but not `threadpoolctl`. What can go wrong, and why does `pip freeze` in a fresh
   venv fix it while `pip freeze` in your everyday environment does not?
4. **Design choice.** The tool compares only the headline values declared in `REPRODUCE.toml`, not the whole
   results file. Defend this, and say what risk it leaves and how you would cover it.
5. SKAB is downloaded from a third party at a pinned commit with hashes. What does the hash protect against, what
   does it not protect against, and what would you do if the upstream repository disappeared?

## Interview rep (15 min, project explanation)

> "How do I know the numbers in your project are real?"

Answer aloud in 3 minutes. Then answer these follow-ups without notes, 1 minute each: "What happens if I clone it
today?", "Which number would you least trust, and why?", "What did the audit find the first time you ran it?",
"How long does a full reproduction take, and on what hardware?". Score yourself with the rubric in the answers file.
