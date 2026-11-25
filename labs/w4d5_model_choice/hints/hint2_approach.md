# Hint 2: approach

`measure_latency`

```text
durations = []
for i in range(n_warmup + n_repeat):
    batch = rows (i*batch_size) % n ... wrapping, batch_size of them
    t0 = clock(); scorer.score(batch); t1 = clock()
    if i >= n_warmup: durations.append((t1 - t0) * 1000)
return dict(n, batch_size, mean_ms, p50_ms, p95_ms, p99_ms, max_ms)   # np.percentile defaults
```

`dominated_by`: build a matrix `v` (rows = candidates, columns = oriented objectives) and, for each
`i`, collect every `j != i` with `(v[j] >= v[i]).all() and (v[j] > v[i]).any()`.

`decision_table`: copy the input into a DataFrame, add three columns, keep the row order.

`recommend`: boolean mask from the constraints → `ok`; `better = ok[ok.vs_reference == "better"]`;
`pool = better if len(better) else ok[ok.vs_reference != "worse"]`; sort `pool` by
`[complexity, primary]` with `ascending=[True, False]`; handle the empty cases with `choice=None`.

Challenge: group row indices by region once; per bootstrap replicate draw region indices with
replacement, concatenate their row indices, compute both AUCs on the same rows, store the difference.
