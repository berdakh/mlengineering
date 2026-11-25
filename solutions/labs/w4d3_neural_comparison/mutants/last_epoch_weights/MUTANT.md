# Mutant: the last epoch's weights are returned

Early stopping halts training but forgets to restore the best checkpoint, so the model reported
is `patience` epochs past its best validation loss. Caught by: the early-stopping check, which
builds a case where validation loss is minimal mid-training.
