# w8d5 assessment

## Reasoning questions (answer in 2-4 sentences)

1. Why does the Limitation beat come *before* Next step, and what happens to a talk that ends on Evidence?
2. Your best test number is 0.92 for a model you did not ship. Should it appear on your results
   slide? Explain your choice (design-choice question).
3. An interviewer asks "is 0.88 good?". Give the two comparisons that make the number interpretable.
4. Why is showing a failure example a stronger move than showing a second success?
5. A question targets a weakness you had not thought of. What do you say in the first ten seconds?
6. Which of your twenty answers had no artifact behind it, and what does that tell you about the project?

## Rubric for the recorded 5-minute walkthrough

| Row | Meets | Partly | Not yet |
|---|---|---|---|
| Structure | six beats in order, each audible; under 5:30 | one beat missing or merged | no discernible structure |
| Decision | the choice and the rule it was made by are explicit | choice stated, rule implicit | method described, no decision |
| Evidence | one headline number with its comparison and interval | numbers without comparison or interval | no numbers, or a list of many |
| Limitation | names a limitation that matters for the decision | generic caveat ("more data") | none |
| Delivery | speaks to a non-specialist; jargon explained; not read verbatim | some jargon unexplained | reads the script |

## Rubric for the twenty answers and the research walkthrough

| Row | Meets | Partly | Not yet |
|---|---|---|---|
| Honesty | concedes real weaknesses; states what is not established | hedges without specifics | defends everything |
| Grounding | each claim points to an artifact; numbers match it | some unsupported claims | invented or unsourced numbers |
| Brevity | 40-130 words, answer first | answer buried in context | over 150 words |
| Research translation (challenge) | concrete counterparts (unit, event, error costs) and two engineering concerns the study lacked | analogy without specifics | none |

## Common incorrect answers and why they fail

* **"The test score was best, so we shipped it."** Ignores the protocol-B result and the cost columns.
* **"Seven experiments is enough because they have 9,000 samples."** Confuses samples with
  independent units - the core error the course is built against.
* **"The drift monitor detects faults."** It detects input change; conflating the two is a red flag.
* **Answers that list everything** ("we also tried X, Y, Z...") instead of answering first.

## Interview rep (10-15 min, reduced assistance)

Record the 5-minute walkthrough without notes. Then draw three question numbers at random
(`python -c "import random; print(sorted(random.sample(range(1, 21), 3)))"`) and answer them aloud,
45 seconds each, before reading your written answers. Score with the rubric above, then compare with
`solutions/lessons/w8d5_project_explanation/QUESTION_BANK.md`.
