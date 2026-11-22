# Hint 3 (partial implementation)

```python
def build_model(args):
    config = tomllib.loads(Path(args.config).read_text())
    unknown, missing = set(config) - MODEL_KEYS, MODEL_KEYS - set(config)
    if unknown or missing:
        print(f"error: unknown {sorted(unknown)}, missing {sorted(missing)}", file=sys.stderr)
        return 2
    manifest = load_splits(args.splits)
    tidy = load_raw(args.raw)
    dev = tidy[tidy["experiment_id"].isin(set(dev_experiments(manifest)))]
    dev_hash = hashlib.sha256(pd.util.hash_pandas_object(dev, index=False).to_numpy().tobytes()).hexdigest()
    provenance = {"config": config, "config_sha256": file_sha256(args.config),
                  "splits_sha256": file_sha256(args.splits), "dev_data_sha256": dev_hash}
    save_bundle(ZScoreModel(**config), args.out, provenance)
    return 0
```

```make
model: $(MODEL_DIR)/MANIFEST.json

$(MODEL_DIR)/MANIFEST.json: $(CONFIG) $(SPLITS) $(wildcard src/flowguard/*.py)
	$(PY) -m flowguard build-model --config $(CONFIG) --splits $(SPLITS) --raw $(RAW) --out $(MODEL_DIR)
```

Still to do: `predict-batch`, the version, the remaining Makefile targets, API and parity tests, README,
CHANGELOG.
