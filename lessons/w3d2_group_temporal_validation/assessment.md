# w3d2 assessment

Answer in writing before opening `solutions/lessons/w3d2_group_temporal_validation/assessment_answers.md`.
Questions 1-3 are on the essential path (10 minutes).

## Reasoning questions

1. A model will score sensor windows from *new* machines next quarter. Name the scheme you would use and
   what it must withhold. Which single scheme would you add as a stress test, and what would a large drop
   on it mean?
2. Features use a 60-row trailing window; the label is "a fault occurs within the next 15 rows". You use
   blocked K-fold within each machine. How many rows do you purge and embargo on each side, and what does
   that buffer *not* protect against?
3. On SKAB, scheme 1 gives 0.985 and scheme 4 gives 0.818 for the forest. A colleague says "the forest
   overfits; use stronger regularisation". What is the better explanation, and which experiment would
   distinguish the two?
4. 25,000 rows from 25 experiments, row-level accuracy 0.90. Someone reports a 95 % interval of
   ±0.004. With within-experiment correlation of correctness $\rho_e = 0.1$ and about 1,000 rows per
   experiment, what is the design effect, and roughly how wide should the interval be?
5. Why does `TimeSeriesSplit(gap=0)` not solve the label-overlap problem, and what does `gap` correspond
   to in section 2.5's notation?
6. In the challenge, why is "opened within the last 26 weeks" the wrong definition of a new store, even
   though it is what the business calls a new store?

## Design-choice explanation (graded)

7. Your validation memo picked scheme 4 as primary and scheme 5 as a stress test. A manager asks you to
   report "the most conservative number" (scheme 6, 0.487 for the forest) in the product review. Write
   the reply (5-8 sentences).

### Rubric for question 7

| Level | Description |
|---|---|
| Strong | Explains that schemes estimate different quantities and that "conservative" is not a criterion; shows why scheme 6 is uninformative here (two folds, day confounded with family, first fold on one overlap group); offers what the review needs: the primary estimate with its uncertainty and the stress-test result as a stated risk |
| Adequate | Correct that scheme 6 answers a different question, without the specific reasons it is unreliable |
| Weak | Agrees to report the lowest number "to be safe", or dismisses scheme 6 because it is low |

## Interview rep (validation and leakage, 15 minutes, spoken)

> "We forecast hourly electricity demand per building for the next 24 hours. Our data science team
> reports MAPE 3 % with 5-fold cross-validation on two years of hourly data from 400 buildings. We plan
> to roll the model out to 2,000 new buildings next month. How would you validate it?"

Cover: the deployment sentence, what must be withheld (time *and* buildings), the gap or purge for a
24-hour horizon and lagged features, seasonality in fold design, what you would report and in how many
numbers. Self-score with the rubric in the answers file.
