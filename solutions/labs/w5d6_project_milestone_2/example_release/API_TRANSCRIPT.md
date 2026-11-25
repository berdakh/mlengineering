# API transcript: a real server on 127.0.0.1 (reference project, real bundle)

Started from `../lab` with

```bash
FLOWGUARD_MODEL_DIR=models/current PYTHONPATH=src python -m uvicorn --factory flowguard.api:app_from_env --host 127.0.0.1 --port 8765
```

bound to the loopback interface only, queried with curl, and stopped afterwards. The `/predict` body
holds the first 100 flow-rate readings of test experiment `valve1/13` as burn-in and four readings from
rows 100, 400, 700 and 1000 as values; only row 700 lies inside the labelled anomaly (rows 570-968).

```text
$ curl -s http://127.0.0.1:8765/healthz
{"status":"ok"}
$ curl -s http://127.0.0.1:8765/readyz
{"status":"ready","model_version":"flowrate-z-2026.11"}
$ curl -s http://127.0.0.1:8765/version
{"package_version":"0.6.0","api_schema":"flowguard-api/1","model_version":"flowrate-z-2026.11"}
$ curl -s -X POST http://127.0.0.1:8765/predict -H "content-type: application/json" -d @body.json
{"model_version":"flowrate-z-2026.11","threshold":7.2441307141,"scores":[1.6836449067741457,0.5523965111716007,19.520823524338255,0.5493247011289982],"above_threshold":[false,false,true,false]}
$ curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8765/predict -H 'content-type: application/json' -d '{"burn_in": [1.0], "values": [2.0]}'
422
```

Values sent: 32.9738, 32.0275, 24.0, 32.0288 (L/min). The anomalous reading (24.0) scores 19.5, far above
the threshold 7.24; the three normal readings score below 2.

Server log (uvicorn 0.54.0):

```text
INFO:     Started server process [8351]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8765 (Press CTRL+C to quit)
INFO:     127.0.0.1:56592 - "GET /healthz HTTP/1.1" 200 OK
INFO:     127.0.0.1:56606 - "GET /readyz HTTP/1.1" 200 OK
INFO:     127.0.0.1:56618 - "GET /version HTTP/1.1" 200 OK
INFO:     127.0.0.1:56626 - "POST /predict HTTP/1.1" 200 OK
INFO:     127.0.0.1:56628 - "POST /predict HTTP/1.1" 422 Unprocessable Content
INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [8351]
```
