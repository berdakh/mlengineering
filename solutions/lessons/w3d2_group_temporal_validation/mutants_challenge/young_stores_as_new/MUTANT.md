# Mutant `young_stores_as_new`

**Mistake.** "New store" is defined by age (opened within 26 weeks of the cut-off) instead of by what the model has seen. Most of these stores have months of training rows.

**Why plausible.** It is the business definition of a new store, and it yields a comfortably large `val_new`. But the deployment question is about stores the model has *never been trained on*; a store-memorising model does well on 'young' stores it has seen.

**Caught by.** `test_known_and_new_stores_are_separated_by_what_the_model_has_seen` and `test_new_store_error_is_not_flattered_by_known_stores`.
