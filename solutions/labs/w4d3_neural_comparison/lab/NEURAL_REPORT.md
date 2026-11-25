# Neural versus classical on SKAB: report (reference)

## Set-up actually used

* Python 3.13.18, torch 2.15.0+cu132 (CPU only), NumPy 2.5.3, scikit-learn 1.9.1
* torch threads: 1 (`--threads 1`, recorded in the output JSON)
* Authoring container, 4 vCPUs

## Results

```text
2. Chosen neural configuration, 5 seeds (FIT -> early stop on VAL -> TEST)
   seed 0: VAL 0.716  TEST 0.724  best epoch 29 (stopped 29)  8 s
   seed 1: VAL 0.744  TEST 0.837  best epoch 4 (stopped 8)  3 s
   seed 2: VAL 0.761  TEST 0.815  best epoch 10 (stopped 14)  4 s
   seed 3: VAL 0.636  TEST 0.682  best epoch 29 (stopped 29)  8 s
   seed 4: VAL 0.741  TEST 0.711  best epoch 28 (stopped 29)  8 s
   TEST over seeds: mean 0.754, sd 0.068, range [0.682, 0.837]

3. TEST, pooled PR-AUC with 95% cluster-bootstrap interval over the 7 test experiments
| neural AE (seed 4, median seed by VAL) | 0.711 [0.546, 0.853] |
| Mahalanobis burn-in (shrinkage 0.3) | 0.768 [0.625, 0.871] |
| flow_rate |z| burn-in (w2d6 best single sensor) | 0.884 [0.811, 0.928] |
   neural minus Mahalanobis burn-in (shrinkage 0.3): -0.057 [-0.194, +0.104]
   neural minus flow_rate |z| burn-in (w2d6 best single sensor): -0.173 [-0.327, -0.035]

4. Cost (this machine)
   neural: 3658 parameters, 6 s training per seed, 6.5 ms per 1000 rows scored
   Mahalanobis: no training, 1.7 ms per 1000 rows scored
```

## Questions

1. **Seed spread versus test interval.** The seed sd is 0.068 (range 0.155). The 95% test interval of one
   fitted model is about 0.31 wide (0.546-0.853), roughly a half-width of 0.15. The test-set interval is
   about twice the seed range. More seeds would pin down the seed *mean* (its standard error with 5 seeds
   is about 0.03) but cannot shrink the test interval; only more test experiments can. Five seeds are
   enough to show that single runs are unreliable; twenty would not change the conclusion.

2. **VAL better, TEST worse.** (a) Selection optimism: the neural family's four VAL scores spread from
   0.605 to 0.716, the Mahalanobis ones from 0.663 to 0.666; picking the maximum of a noisier family
   inflates it more (w3d3). (b) Distribution difference: the 6 VAL experiments are not the 7 TEST
   experiments; the AE may model the fault types in VAL better by chance. Distinguishing them: nested
   validation over all 27 dev experiments (rotate which fold is VAL) gives an estimate of the whole
   procedure without touching TEST; per-experiment VAL and TEST scores show whether one or two
   experiments drive the gap.

3. **Which seed.** If forced: the median seed by VAL (seed 4), or better an ensemble averaging the scores
   of all five, which removes most of the seed lottery at five times the cost. Choosing by TEST score is
   selection on the test set: the reported number would then be the maximum of five noisy draws
   (expected optimism several points, worked example), and the test set would no longer be an unbiased
   check for anything.

4. **Recommendation.** Carry the burn-in flow-rate z-score and Mahalanobis detectors forward to Week 5;
   do not ship the autoencoder. The evidence supports only "no detectable improvement from a small conv
   autoencoder under an equal four-configuration budget on 21 training experiments"; it does not show
   that neural models cannot help. Revisit if more experiments become available (especially new fault
   families), if raw high-rate signals are added, or if a nested estimate over all development folds
   shows a consistent gain larger than the seed spread.
