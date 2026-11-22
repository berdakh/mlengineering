# Model answers — w4d4 experiment tracking

## A. Reasoning questions

1. **Same config, different metrics.** (a) Different code: `environment.json: git_commit` differs, or ends
   in `-dirty` (uncommitted changes). (b) Different data at the same path: the data fingerprint differs.
   (c) Different library versions or platform (numerics, defaults changed between versions):
   `environment.json: packages`, `platform`. (d) Non-determinism not controlled by the seed (threads, GPU
   kernels, unordered iteration): nothing in the record differs, which is itself the diagnosis; rerun twice
   on one machine to confirm, and record thread count and device. *Common wrong answer:* "the seed
   differed". Then the configs, which include the seed, would differ too.

2. **Seed in the id.** Identity means "this exact computation". Two seeds are two computations with
   different results; if they shared an id, the second would be skipped as already complete (or overwrite
   the first), and the table would show `n = 1` where you asked for several. Selection ignores the seed;
   identity cannot.

3. **Keeping only the index.** Lost: the full resolved configs (the index flattens them but a CSV loses
   types), the environment and data fingerprints, the error records of failed runs, any artifacts, and the
   ability to reproduce or rebuild the table if the CSV is wrong. Keep the small files (`config.json`,
   `environment.json`, `metrics.json`, `status.json`, typically kilobytes) for every run and delete only
   large artifacts of runs that were never selected, recording that they were deleted.

4. **Excluded run.** Failed (the task raised; `status.json` holds the error) or partial (no
   `status.json`: the process died, or is still running). A failed run needs a diagnosis: if the failure
   depends on the configuration (for example a numerical error at extreme hyperparameters) it is a
   *result* to report, not something to hide by rerunning until it passes. A partial run should be
   re-executed (the sweep does so automatically) once you know it is not still running. Until then the
   configuration has fewer seeds than the others, which should be visible.

5. **Different scored rows.** Configurations with a shorter burn-in would be evaluated on more rows,
   including rows 100-199, which are close to the start of each experiment and almost always normal, so
   their metrics would be computed on an easier, different set. The comparison would mix the effect of the
   parameter with the effect of the evaluation set. Fixed evaluation rows make the configurations
   comparable.

## B. Design choice: directories versus database

Directories as truth are better for a single researcher or a small team on shared storage: no service to
run, results travel with `cp`/`rsync`, the record is human-readable, and the index can always be rebuilt.
They make it easy to have *several* inconsistent copies (two machines each with half the runs) and they
scale poorly to millions of runs or concurrent writers. A database (MLflow's backend store) is better for
many people and many concurrent runs, with queries and a UI; it makes it easy to lose the link between
the database row and the actual artifacts (a database restored from backup while the artifact store moved
on) and harder to inspect or repair by hand. Either way, the record must be immutable once complete.

## C. Rubric

See `assessment.md`. "Strong" on provenance requires naming the dirty flag and a data fingerprint, and
what each would catch (uncommitted code; a changed file at the same path).

## D. Interview rep

Reference with tests: `interview_rep/config_diff.py`. Complexity: `diff_configs` is O(n) in the total
number of leaves of both configs (flattening plus set operations on hashed keys); `best_per_group` is
O(R · g) for R records and g grouping keys (one pass, constant work per key lookup).

| | Weak | Solid | Strong |
|---|---|---|---|
| Correctness | misses nested keys or removed keys | passes the examples | also handles a table replaced by a scalar, ties, non-complete runs |
| Design | ad-hoc recursion with global state | a flatten helper | flatten helper reused by both functions, no mutation of inputs |
| Complexity | not stated | stated | stated with the reason (hashing, single pass) |
| Testing | none | runs the examples | adds an edge case of their own |
