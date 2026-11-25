# Answers to the twenty questions (reference)

Every number below comes from the cited lesson's own runs on the SKAB data (or, where stated, on
synthetic data). They are the course author's reference answers; yours should cite your project.

## Q01

I found it while building the data skeleton: 1,290 rows are identical in all sensors and timestamp
across five pairs of files, and 235 of them carry contradictory anomaly labels. Two consequences. A
row-level or even experiment-level split could put the same physical minute in train and test, so I
compute overlap groups and keep each group on one side; the frozen manifest v2 does that without
redrawing the test set. And 235 rows have no single correct label, which bounds how well any
detector can score near those boundaries.

Evidence: `project/README.md` `lessons/w3d1_leakage/README.md`

## Q02

That the benchmark encodes its protocol: in 31 of 34 experiments the fault starts around row 550-600,
so elapsed time alone gets F1 0.835 on the original test set. It tells me two things. Any feature
that is monotone in time is a leak of the experimental protocol, so `t` and timestamps are forbidden
inputs. And any sensor model must be compared against the clock, not only against chance; I keep the
clock as a sanity row in every evaluation table.

Evidence: `lessons/w2d6_baselines_metrics/README.md` `docs/FLOWGUARD_SPEC.md`

## Q03

They should believe the intervals more than the point estimates. Seven test experiments means event
recall of 5 of 7 has a 95 % interval of roughly 0.36 to 0.92, so I never claim small differences on
test. I resample whole experiments for intervals, I made every selection decision on the 27
development experiments, and the test set got one look. What I can say is "clearly better than the
clock and than chance", not "two points better than the alternative".

Evidence: `lessons/w4d5_model_choice/figures/test_look.csv` `lessons/w3d5_uncertainty/README.md`

## Q04

Because the test score answered the wrong question. Boosted trees reached PR-AUC 0.920 when test
faults came from fault families seen in training, but 0.636 when I held out the whole unseen
"other" family, the level of a single z-score, while isolation forest and PCA T-squared held up.
A plant meets new fault types. A supervised model trained on labelled valve faults is supported by
the labels for valve faults only, so I treated its win as narrow, not general.

Evidence: `lessons/w4d2_classical_detectors/README.md`

## Q05

I tried one, under the same protocol and tuning budget: a small convolutional autoencoder, five
seeds. Test PR-AUC was 0.754 on average with a standard deviation of 0.068 across seeds, against 0.884
for the burn-in flow-rate z-score. So the neural model was neither better nor stable enough to
justify its cost. With 34 labelled experiments and one-hertz signals I would not expect a large model
to win; I would revisit it with far more recordings. To be completely thorough about this, I also want to mention every other consideration that came up, To be completely thorough about this, I also want to mention every other consideration that came up, To be completely thorough about this, I also want to mention every other consideration that came up, To be completely thorough about this, I also want to mention every other consideration that came up, 

Evidence: `lessons/w4d3_neural_comparison/README.md`

## Q06

The project is the evaluation and the service, not the model. On development data the best
alternative, logistic regression, was ahead by 0.069 with an interval of 0.022 to 0.128, which my
pre-set rule called inconclusive against a minimum important difference of 0.05. The z-score is
370 bytes, needs only NumPy, scores a sample in a fraction of a millisecond and an engineer can read
it. Choosing the simple model when evidence does not separate candidates is a decision I can defend.

Evidence: `lessons/w4d5_model_choice/figures/decision_table.csv` `lessons/w4d5_model_choice/README.md`

## Q07

On development data only. I fixed an alert budget first, then chose the threshold and the
post-processing that maximise event recall within that budget on the 27 development experiments:
threshold 7.24, a 30-sample minimum duration. The test set got one look after the decision memo was
written. Nested validation on the same data showed how optimistic picking the best of many trials is,
which is why the single test look matters.

Evidence: `lessons/w4d5_model_choice/figures/decision_table.csv` `lessons/w3d3_hyperparameter_selection/README.md`

## Q08

Both, with event-level as the decision metric. Point metrics reward long segments and late detections
and ignore false alarms between events; the engineer experiences events: was the fault caught, how
late, how many false alarms per hour. I also show why the common "point-adjust" scoring is misleading:
it lets almost any scorer look good. Event metrics do not fix leakage, though: the clock still finds
3 of 7 test faults.

Evidence: `lessons/w3d4_point_vs_event_evaluation/README.md`

## Q09

No, it answers a different question. Input drift monitoring tells me the inputs no longer look like
the reference, which catches recalibrations, broken sensors and new regimes; on real replays it
flagged only 14-20 % of fault windows, so it is not a fault detector and I never presented it as
one. Fault detection is the model's job; "is the model still good" needs delayed labels. Three
monitors, three questions.

Evidence: `lessons/w7d2_input_monitoring_drift/README.md` `lessons/w7d3_drift_vs_degradation/README.md`

## Q10

It degrades explicitly. Invalid input is rejected at the boundary with a 422 naming the field;
legal but out-of-support input is scored and flagged. If the model cannot load, readiness reports
not ready, and scoring falls back to a simple envelope rule with `degraded: true` in every response
and a metric. I measured the cost: the fallback catches 2 of 7 test faults against 5 of 7 for the
model, so degraded mode must be visible, never silent.

Evidence: `lessons/w7d5_reliability/README.md`

## Q11

Nagle's algorithm. With one worker latency was fine; with two or four workers uvicorn's
multi-process mode left Nagle on, and the delayed-ACK interaction added about 40 ms to every small
response. I confirmed it from the installed source and by forcing TCP_NODELAY in an experiment:
median latency at 60 requests per second fell from 52 to 9.5 ms. The lesson: measure percentiles
under load, change one thing, and confirm the mechanism before fixing.

Evidence: `lessons/w6d4_latency_resources/README.md`

## Q12

By test, not by trust. One object owns burn-in state, features and scoring, and the evaluation, the
batch command and the API all call it. A parity test compares the three paths: differences were
exactly zero over all 46,806 rows of the 35 experiments, and streaming replay matched batch within
1e-12. One finding: pandas' default CSV float parser is not round-trip exact, so the contract reads
with `float_precision="round_trip"`.

Evidence: `lessons/w5d6_project_milestone_2/README.md` `lessons/w5d3_online_inference/README.md`

## Q13

Because ties at a threshold turn rounding into decisions. When I checked that a sensor
recalibration does not change which faults are caught, 198 samples scored exactly at the threshold, so
a 1e-14 difference flipped their flags. The caught faults were identical, but per-sample alarm logs
differed. In production that means a deterministic tie rule, a comparison that is documented as `>`
or `>=`, and parity tests with tolerances chosen on purpose.

Evidence: `lessons/w7d3_drift_vs_degradation/README.md`

## Q14

From delayed labels, joined back to logged predictions, plus proxies I trust less. In a replay where
a bad release doubled the threshold, recall fell from 11 of 20 faults to 4 of 20 and the drift
monitor stayed quiet. The labelled estimate was "unknown" at first and still inconclusive months
later because few events arrive. So the honest plan is: alert rate and score distribution as early
proxies, labelled event recall with intervals as the verdict.

Evidence: `lessons/w7d3_drift_vs_degradation/README.md`

## Q15

Gate, shadow, promote, keep rollback one step away. The candidate must pass an offline gate:
a paired comparison on the frozen protocol with a non-inferiority margin. A re-tuned version passed
at +0.143 with an interval from 0.000 to 0.429. Then shadow mode scores live traffic without serving
it. A pitfall I found: the shadow traffic contained no "other" family, where all the candidate's false
alarms were. Rollback is a registry pointer move, verified byte-identical.

Evidence: `lessons/w7d4_model_updates_rollback/README.md`

## Q16

First, more independent experiments: with seven test experiments, everything I would like to
claim is under-powered, so data collection beats modelling. Second, label quality: resolve the 235
contradictory rows with whoever ran the testbed. Third, a supervised model per fault family with
proper leave-family-out evaluation, since the unseen-family result is the real risk. Fourth, run the
monitoring stack on live data for weeks to calibrate alert thresholds.

Evidence: `project/README.md` `lessons/w3d5_uncertainty/README.md`

## Q17

Almost anything about a real plant. SKAB is a laboratory testbed with 34 short experiments, one fault
each, induced on purpose, and about 35 % anomalous samples - real faults are rare and unplanned. The
labels come from the experimenters, not from maintenance logs. So my numbers show that the method and
the engineering work on this testbed; real false-alarm rates, lead times and value need a pilot on
the target equipment.

Evidence: `project/README.md`

## Q18

Because the experiment is the independent unit, as the patient is in my EEG work: samples within an
experiment are strongly correlated, and the deployment question is a new run. Row-level 4-fold
cross-validation reported ROC-AUC 0.986; experiment-level gave 0.849 on the same development data. The
cost is fewer, noisier folds and wider intervals - the price of measuring the right thing.

Evidence: `lessons/w2d4_problem_framing_splits/README.md`

## Q19

Because resampling samples pretends I have tens of thousands of independent observations when I have
a few dozen experiments. On this data, row-level bootstrap intervals were 3 to 7 times too narrow;
a coverage simulation with clustered data showed the same. The cluster bootstrap resamples whole
experiments, keeps their internal dependence and gives intervals that cover. With 7 test
experiments I also check intervals against exact binomial ones for event recall.

Evidence: `lessons/w3d5_uncertainty/README.md`

## Q20

The modelling instincts transfer: units of independence, event-level scoring, artefacts, drift
between sessions. What is new is everything after the model: a package with tests and CI, a
versioned artifact, an API with explicit failure modes, a container, a gated deployment path,
monitoring that separates input drift from degradation, and rollback. In research a result ends
in a paper; here it has to keep working on data nobody has seen yet.

Evidence: `handbook/README.md` `ROADMAP.md`
