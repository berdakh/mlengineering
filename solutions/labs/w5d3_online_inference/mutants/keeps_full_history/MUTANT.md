# Mutant: keeps_full_history

Stores every accepted value in a list and recomputes the burn-in statistics from it. Scores are
correct, but memory and snapshot size grow without bound with the stream: a process that monitors a
pump for a year eventually runs out of memory, and every checkpoint gets slower.
