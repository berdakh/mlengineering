# Hint 2 (approach)

1. Delete the arithmetic in `api.py`'s `predict`; call `model.score(body.burn_in, body.values)` and
   `model.above_threshold(scores)`.
2. `build-model`: `tomllib.loads(config_path.read_text())`; check the keys against `MODEL_KEYS`;
   `load_splits(args.splits)`; hash files with `file_sha256`; identify the development rows (for example
   a hash of `pandas.util.hash_pandas_object` over them); `save_bundle(model, out, provenance)`.
3. `predict-batch`: `load_bundle` inside `try/except BundleError` (print, return 2); `_select` the split;
   `score_experiments`; `to_csv(..., float_format="%.17g")`.
4. Version: `dynamic = ["version"]` plus `[tool.setuptools.dynamic] version = {attr = "flowguard.__version__"}`.
5. Makefile: make `models/current/MANIFEST.json` a file target that depends on the config, the manifest
   and `src/flowguard/*.py`; `model` depends on it. `export PYTHONPATH := src` so no install is needed.
6. Parity test: a shuffled synthetic tidy table of three experiments; compare `score_experiments`,
   `experiment_scores` and the API (chunk the values to exercise chunking) with `atol=1e-12`.
