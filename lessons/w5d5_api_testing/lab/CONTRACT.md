# Service contract: flowguard API, schema `flowguard-api/1`

This is the behaviour your tests must pin down. The code is in `service/flowguard/`; read it only
after writing a test, to find out why a test fails, not to decide what to test.

## Model and bundle

* A bundle is a directory with `model.json` and `MANIFEST.json`. `MANIFEST.json` holds
  `schema = "flowguard-bundle/1"`, `package_version`, and a SHA-256 for every file.
  Create one with `flowguard.bundle.save_bundle(ZScoreModel(...), directory)`.
* Loading (`load_bundle`) raises `BundleError` when the manifest is missing or unreadable, the schema
  is unknown, a listed file is missing, or **a checksum does not match**.
* `ZScoreModel(sensor, n_burn_in, threshold, min_duration, merge_gap, model_version)`:
  `score(burn_in, values) = |values - mean(burn_in)| / std(burn_in)` with the **population** standard
  deviation (ddof = 0, as in training); a burn-in with zero spread uses std = 1.
  A value is above threshold when **score >= threshold**.

## Lifecycle

* `create_app(model_dir)` builds the app **without** loading the bundle. The bundle is loaded at
  startup (the lifespan). Use `with TestClient(app) as client:` to run startup in tests.
* If loading fails, the process still starts (degraded): `/healthz` is 200, `/readyz` is 503 with a
  reason, `/predict` is 503.

## Endpoints

| Method, path | Success | Errors |
|---|---|---|
| `GET /healthz` | 200 `{"status": "ok"}` whenever the process runs | - |
| `GET /readyz` | 200 `{"status": "ready", "model_version": ...}` once a bundle is loaded | 503 `{"status": "not ready", "reason": ...}` |
| `GET /version` | 200 `{"package_version", "api_schema": "flowguard-api/1", "model_version"}` (`null` if not loaded) | - |
| `POST /predict` | 200 `{"model_version", "threshold", "scores", "above_threshold"}`; one score and one flag per value, in order | 422 invalid body; 413 too many values; 503 no model |

`POST /predict` body (JSON object, no other fields allowed):

| Field | Type | Rules |
|---|---|---|
| `burn_in` | array of numbers | 2 to 3600 items, all finite |
| `values` | array of numbers | at least 1 item, all finite; more than 3600 items -> **413** |

* Unknown fields -> 422. Non-finite numbers (`NaN`, `Infinity`, which some JSON encoders emit) -> 422.
* 422 responses list errors as `{"loc", "msg", "type"}` and do not echo the input.
* Responses are deterministic: the same request always gives the same body, also under concurrent load.
