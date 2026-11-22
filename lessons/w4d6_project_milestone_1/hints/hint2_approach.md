# Hint 2: approach

Makefile:

```make
SRC := $(wildcard src/flowguard/*.py)

$(TIDY): $(wildcard $(RAW)/*/*.csv) src/flowguard/data.py src/flowguard/pipeline.py
	$(PY) -m flowguard ingest --raw-dir $(RAW) --out $@

$(RESULTS): $(TIDY) $(SPLITS) $(SRC)
	$(PY) -m flowguard evaluate --tidy $(TIDY) --splits $(SPLITS) --out $@ --burn-in $(BURN_IN) --n-boot $(N_BOOT) --seed $(SEED)
```

The report rule is the same shape. `clean` is one `rm -rf` of three directories.

`evaluate`, in order:

1. Read the tidy CSV (`read_tidy`) and the manifest; validate.
2. Split into dev and test frames; map experiments to clusters (overlap groups).
3. For each candidate, compute out-of-fold dev scores, the per-cluster `(y, score)` pairs, and a
   cluster-bootstrap PR-AUC. Then the operating point (`choose_operating_point` on dev) and the size
   of the calibrated step.
4. Paired differences to the reference; `decision_table`; `recommend`.
5. Test: score every candidate once, apply its dev operating point, then `evaluate_experiments` and
   `wilson_interval`.
6. Per-experiment rows for the chosen candidate; per-family dev recall.
7. Return the dict with `provenance` and `protocol.test_experiments`.

`render`: one list of lines, appended section by section; `"\n".join(lines)`.
