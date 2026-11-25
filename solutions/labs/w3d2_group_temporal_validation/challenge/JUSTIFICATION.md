# Store-demand validation: justification (reference)

**Deployment sentence.** At the end of week *c* the model is retrained on everything known by then and
used for weeks *c+1 .. c+8*, for existing stores and for stores it has never seen.

**Rules.**

* `train`: labelled rows with `week + 4 <= c`. A label at week *t* is the demand of weeks *t+1..t+4*;
  it is known only once week *t+4* has happened. Rows with `c-3 <= week <= c` have a date before the
  cut-off but a label that did not yet exist: they are the purge, here `label_weeks` rows wide because
  the label horizon is 4 and the features use only week *t*.
* validation: labelled rows with `c < week <= c + 8`, the period in which the model is used.
* `val_known` / `val_new`: by whether the store has at least one training row, i.e. by what the
  model has seen, not by the store's age.

**Why the random split was too good.** A random 80/20 split of store-weeks puts each store's other weeks
in training (the store attributes identify the store, so the model memorises its level) and puts weeks
on both sides whose label windows overlap (a training label at week 41 shares three weeks of demand with
a validation label at week 42). Measured on the shipped panel with a random forest on log current demand,
store attributes and season: random split MAE 0.123 (log scale); deployment folds at weeks 40, 60, 80:
known stores 0.171, new stores 0.361.

**Report two numbers.** The pooled deployment MAE is 0.187, because new-store rows are only 93 of 1,149
validation rows. A single pooled number hides that new stores are about twice as hard, and the share of
new stores in deployment is a business quantity that will not match this sample.
