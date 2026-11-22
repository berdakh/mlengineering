# Mutant: batch_backdates

`hysteresis_batch` is written as an offline filter: once a run of k exceedances is found, the alarm
is marked from the run's FIRST sample, like `extract_events(min_duration=k)`. It looks like the
same rule, but a stream can only know at the k-th sample, so batch and streaming disagree.
