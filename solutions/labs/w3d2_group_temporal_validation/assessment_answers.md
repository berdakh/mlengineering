# w3d2 assessment - model answers

## 1. New machines next quarter

Grouped by machine **and** later in time: train on machines A and on data up to a cut-off; validate on
other machines after the cut-off (the "new units, later" combination of section 2.6). If only one
condition can be met, grouping matters most when machine identity is learnable; time matters most
when there is drift. Stress test: leave-one-category-out on whatever defines regimes (machine model,
site, firmware). A large drop means the model's performance depends on the regime and the rollout plan
must say which regimes it covers.

*Common incorrect answers.* "TimeSeriesSplit" alone (validation machines are in training). "Grouped
K-fold" alone, when the data span long periods with drift.

## 2. Buffer

$w - 1 + h = 60 - 1 + 15 = 74$ rows each side. It guarantees no raw sample is shared between a training
row and a validation row. It does not protect against: autocorrelation of the raw signal beyond 74 rows,
slow drift, machine identity (validation machine is in training under within-machine blocking), and
protocol effects (e.g. faults always injected at the same time).

*Common incorrect answers.* 60 (forgets the label horizon), 75 (off by one: adjacent rows need $w-1$),
"purge only before" (the embargo is needed in blocked K-fold because later training rows' windows reach
back into the block).

## 3. 0.985 versus 0.818

The gap is mostly **group leakage**, not overfitting in the usual sense: under row splits, validation
rows' experiment-mates are in training, and raw sensor levels identify the experiment. The forest is
not failing to generalise to new rows of a known experiment (it does that very well); it is
generalising to new experiments that is hard. Distinguish: (a) regularise strongly (min_samples_leaf,
max_depth) and rerun both schemes; if it were classic overfitting, scheme 4 would rise substantially; if
it is experiment memorisation, scheme 1 falls toward scheme 4 and scheme 4 barely moves. (b) A
fingerprint probe: train a classifier to predict `experiment_id` from the features; near-perfect
accuracy confirms that rows identify their experiment.

## 4. Design effect

$\mathrm{deff} = 1 + (m-1)\rho_e = 1 + 999 \times 0.1 \approx 101$. The naive standard error
$\sqrt{0.9 \cdot 0.1 / 25{,}000} \approx 0.0019$ (half-width ±0.004) becomes about $0.0019 \times \sqrt{101}
\approx 0.019$, half-width about ±0.04: ten times wider. Effective sample size about 250 rows, i.e. on the
order of the number of experiments.

## 5. `TimeSeriesSplit(gap=0)`

It orders folds so validation follows training, but the last training rows' labels (and the first
validation rows' feature windows) overlap the boundary. `gap` drops that many rows between training and
validation; it corresponds to the **purge** $w - 1 + h$. There is nothing after the validation block in
forward chaining, so no embargo is needed. It also knows nothing about groups.

## 6. "Young" stores

Validation must estimate the error on stores the model *has not seen*. A store opened 20 weeks before
the cut-off has 16 weeks of training rows; a model that memorises stores through `fp_*` predicts it well.
Counting it as new pulls the "new store" error toward the known-store error and hides the cost of a
genuinely unseen store. The business definition is useful for *reporting* (how many deployment stores
will be unseen) but not for building the validation sets. Mutant `young_stores_as_new` is this mistake.

## 7. Reply to the manager (model answer)

"The six schemes do not give more or less cautious versions of one number; each answers a different
question. Scheme 6 asks whether a model trained on earlier recording days works on later ones, but in
this dataset the day determines the fault family, there are only two folds, and the first validates on
three copies of one recording, so its 0.49 tells us almost nothing. The question the product depends on
is whether the detector works on runs it has not seen, and the best estimate of that is 0.82 ROC-AUC
(range over folds 0.63-0.94), with intervals to follow in w3d5. The real risk the review should hear
about is a fault family the detector has never seen: holding out the `other` family, performance falls to
about 0.53-0.65. I recommend we state that the detector is validated for the known families only and
treat new families as out of scope until we have data."

## Interview rep rubric (0-2 each; 9+ is strong)

| Point | 2 | 1 | 0 |
|---|---|---|---|
| Deployment sentence | "24-hour forecast for buildings never seen, starting next month" | mentions new buildings or future, not both | none |
| Withhold both | validation buildings absent from training **and** validation period after training | one of the two | random 5-fold accepted |
| Gap | 24 h horizon + longest lag feature (e.g. 168 h) → gap at least the horizon, plus care for lag windows | mentions a gap without size | none |
| Seasonality | folds span seasons, or the evaluation period matches the rollout season; warns that one month of validation misses winter peaks | mentions seasons | none |
| Reporting | separate errors for known vs new buildings, per horizon hour, with uncertainty across buildings | one pooled number with an interval | one pooled MAPE |

*Typical weak answer.* "Use TimeSeriesSplit" (misses the 2,000 new buildings and the horizon gap) or
"MAPE 3 % is great" (MAPE also misbehaves for near-zero demand, a bonus point if raised).
