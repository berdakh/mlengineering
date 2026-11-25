# Mutant: anomalous rows are part of the training windows

The autoencoder is trained on every row after burn-in, including rows labelled anomalous,
on the argument that anomalies are rare so the model will mostly learn normal behaviour. On SKAB
about a third of the rows are anomalous; the model learns to reconstruct faults. Caught by: the
contamination check (anomalous rows set to 1e6 must not change what is learned).
