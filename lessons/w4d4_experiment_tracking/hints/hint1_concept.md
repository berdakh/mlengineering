# Hint 1 — concepts (w4d4)

* **Identity**: a run *is* its resolved configuration. Anything that changes the result (including the
  seed) must change the id; anything that does not (key order) must not.
* **Truth**: the run directories are the record. Everything else (index, table) is recomputed from them.
* **Completion**: only the last file written can signal that a run finished.
* **Honest tables**: count what you exclude; do not let missing parameter values make rows disappear.
* **Reproduction**: re-execute; never compare a stored number with itself.

Challenge: pairing compares like with like. A difference of means over groups with different seeds is
not a paired comparison, even if most seeds match.
