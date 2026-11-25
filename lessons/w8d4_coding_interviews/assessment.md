# w8d4 assessment

Answer in writing or aloud before opening `solutions/lessons/w8d4_coding_interviews/assessment_answers.md`.

**Q1.** P3 asks for O(n). A colleague keeps a list of kept events and scans it backwards for the same key.
What is the worst-case complexity, and on what input does it happen?

**Q2.** Why does `RANK()` give the wrong answer for Q2 while `ROW_NUMBER()` with a tie-breaker gives the
right one? When would `DENSE_RANK()` be the right choice instead?

**Q3 (design choice — explain).** In P4 you could store all values per sensor and call
`statistics.pvariance`, or use a one-pass update. Compare memory, time and numerical behaviour, and say
which you would choose in an interview and why.

**Q4.** Explain why "binary search on the answer" is valid for P5: what property must the feasibility
check have?

**Q5.** Q1 joins trips to payments. Write down the grain of each intermediate result in your query, and the
invariant you would check (a row count or a total) to prove there is no fan-out.

**Q6.** In P6, why does an iterative algorithm matter in Python specifically, and how does Kahn's
algorithm detect a cycle without a separate search?

**Q7.** You have 25 minutes for a problem and after 10 minutes you have only a brute force. What do you
say and do?

## Interview rep: the set itself

The timed problems in [`PROBLEMS.md`](PROBLEMS.md) and the mock in [`challenge/README.md`](challenge/README.md),
talked aloud and recorded. Score each recording with this rubric before reading the reference notes.

| Behaviour | Demonstrated | Partial | Not yet |
|---|---|---|---|
| Restates the problem with a small example and edge cases | before coding | after starting | never |
| States a brute force and its complexity | yes, in under 2 minutes | complexity missing | skips to code |
| Names the improvement and why it is correct | pattern + invariant | pattern only | trial and error |
| Writes or says own tests, including an edge case | before running checks | only after a failure | none |
| States final time and space complexity correctly | both | one | neither |
| Communicates while stuck | says what is blocking and tries a smaller case | silent stretches > 1 min | silent |
| Finishes within the time box | yes | within +50 % | no |
