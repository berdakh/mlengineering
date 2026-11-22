# Hint 3 (partial implementation)

**Lab: the concurrency test and the tampered bundle.**

```python
def test_concurrent_requests_get_their_own_answers(client):
    def call(i):
        r = client.post("/predict", json={"burn_in": [-1.0, 1.0], "values": [float(i)] * 5})
        assert r.status_code == 200
        return i, r.json()["scores"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(call, range(48)))
    for i, scores in results:
        assert scores == pytest.approx([float(i)] * 5)


def test_tampered_bundle_is_refused(bundle_dir):
    params = json.loads((bundle_dir / "model.json").read_text())
    params["threshold"] = 0.0
    (bundle_dir / "model.json").write_text(json.dumps(params))
    with TestClient(create_app(bundle_dir)) as client:
        assert client.get("/readyz").status_code == 503
```

**Challenge: resolution and type signatures.**

```python
def _resolve(schema, document):
    while isinstance(schema, dict) and "$ref" in schema:
        node = document
        for part in schema["$ref"][2:].split("/"):     # "#/components/schemas/Name"
            node = node[part]
        schema = node
    return schema or {}


def _types(schema, document):
    schema = _resolve(schema, document)
    for key in ("anyOf", "oneOf"):
        if key in schema:
            return frozenset().union(*(_types(s, document) for s in schema[key]))
    if schema.get("type") == "array":
        inner = "|".join(sorted(_types(schema.get("items", {}), document)))
        return frozenset({f"array<{inner}>"})
    ...
```

Request field `f` is broken when `not old_types <= new_types`; response field `f` when
`not new_types <= old_types`. Remaining: required-set differences, removed fields, constraints,
removed endpoints and statuses.
