# Mutant: needs a running server

The tests call `http://127.0.0.1:8000` with httpx, assuming someone started uvicorn first. In the
grading run (and in CI) nothing listens there and the network is blocked, so the suite fails on the
correct service. Rejected: API tests must be self-contained (TestClient + a bundle in tmp_path); a
smoke test against a running process is a separate, later layer.
