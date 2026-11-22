# Model answers — w4d3 neural comparison

## A. Reasoning questions

1. **Objective.** With 27 development experiments and one segment each, a classifier has 27 positive
   examples of "a fault" in effect (thousands of rows, but highly dependent), from three families. It will
   learn those faults; nothing pushes it to flag a new kind. Reconstruction and forecasting learn
   *normal* behaviour from all normal rows, so any departure can raise the score. Switch to a classifier
   when faults are many, of known recurring types, labelled reliably, and the cost of missing a *known*
   type dominates (for example a fleet of 5,000 pumps with hundreds of labelled bearing failures).
   *Common wrong answer:* "classifiers need balanced classes". Balance is not the issue (SKAB is ~35%
   anomalous at row level); the number of independent fault instances and families is.

2. **Early stopping.** The returned model holds the epoch-10 weights (the best validation loss; patience
   4 means epochs 11-14 did not improve). Reporting the epoch-30 TEST score would describe a model nobody
   chose by the stated rule; and choosing between epoch 10 and epoch 30 *by their TEST scores* would be
   selection on test. *Common wrong answer:* "it contains the epoch-14 weights" (that is the last-epoch
   mutant).

3. **Whole-experiment standardisation.** The mean and sd then include the fault rows: a level shift from
   row 600 raises the mean and inflates the sd, so the standardised fault is smaller and the normal part is
   shifted the other way. It is also look-ahead: at row 650 in deployment the statistics of rows 651-1,100
   do not exist yet. Offline scores are computed with information the live detector cannot have, so the
   offline precision will not hold. *Common wrong answer:* "it is fine because no labels are used". Leakage
   of future inputs does not need labels.

4. **Better reconstruction, worse detector.** A model with more effective capacity can reconstruct
   *anything* well, including fault windows, so the error gap between normal and fault rows shrinks.
   Detection needs the error on faults to be large relative to the error on normal rows, which validation
   loss on normal rows does not measure. (The classic over-complete autoencoder problem; the bottleneck is
   the regulariser.) *Common wrong answer:* "seed 3 overfitted". Its validation loss is the lowest, so it
   did not overfit in the usual sense.

5. **Different numbers on another machine.** Thread count (parallel reductions reorder floating-point
   sums; 2.6 measured a change in the third decimal of PR-AUC), torch / BLAS / NumPy versions, CPU
   instruction set (different kernels), a different SKAB download (check the manifest hashes), a
   different manifest. Record: seed, thread count, device, library versions, data and manifest hashes,
   code commit, exactly what w4d4 automates.

## B. Design choice: one thread

For this model (3,658 parameters, batches of 256 windows of 16 x 8) the work per operation is tiny and
thread synchronisation dominates: on the authoring container a 6-epoch fit took 1.6 s on one thread and
94.5 s on four. One thread also fixes the order of floating-point reductions, so two runs with the same
seed are bitwise identical on the same machine. Both properties are recorded in the output so the
choice is visible. For a large production model this choice is wrong: it would waste most of the
hardware. There you would use many threads or a GPU, accept that runs are reproducible only up to
numerical noise, quantify that noise by repeating seeds, and pin library versions and hardware type in
the run record instead of relying on bitwise equality.

**Rubric:** strong answers give the measured reason (overhead versus work), the reproducibility reason,
and the production caveat; solid answers give one reason and the caveat; weak answers say "for
reproducibility" only.

## C. Rubric usage

Use the table in `assessment.md`. "Strong" on uncertainty requires naming both the seed spread and a
test-set interval and saying which question each answers.

## D. Interview rep — worked answer and rubric

A strong narrative goes from cheapest-and-most-likely to expensive, and says why:

1. **Validation windows are not held out.** `train_test_split` on windows splits *overlapping* windows
   of the *same experiments* at random: almost every validation window has near-copies in training (31
   of its 32 rows shifted by one). Validation loss near zero is the symptom. Fix: split by experiment
   (dev folds), as in w3d1/w3d2.
2. **Anomalous rows are in training.** Nothing filters `anomaly == 0` or the burn-in rows; the model
   learns to reconstruct faults, which explains misses in deployment. Fix: train on normal, post-burn-in
   rows only.
3. **Windows cross experiment boundaries.** `make_windows` over the concatenated frame produces windows
   that end in one experiment and start in the previous one. Fix: window per experiment.
4. **Normaliser fitted on all training rows including faults**, and later probably on the scored data.
   Fix: fit on the usable training rows, store it, never refit.
5. **`best_state = model.state_dict()` without a copy**: the "best" weights are the live tensors, so the
   restored model is the last epoch's. Fix: `copy.deepcopy`.
6. **No seeds, `num_workers=4`, `shuffle=True` without a generator**: runs are not reproducible, so
   "it worked offline" cannot be re-checked. Fix: seed model, generator and workers; record threads.
7. Only then: deployment-side differences (causal scoring, sensor scaling in production, the live
   normaliser).

| | Weak | Solid | Strong |
|---|---|---|---|
| Finds the leak | misses it | names random window split | explains overlap and why validation loss collapses |
| Training data | misses faults in training | names it | connects it to the shadow-deployment misses |
| Code-level bugs | none | state_dict or boundary windows | both, with fixes |
| Order and reasoning | list without order | rough order | cheapest/most likely first, says what each check would show |
