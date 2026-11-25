"""Where does one /predict request spend its time? (given)

    python labs/w6d4_latency_resources/lab/profile_predict.py [--batch 600] [--repeat 50]

Two views, both in-process (no network, no uvicorn):
1. **Spans**: the request path re-enacted step by step with time.perf_counter around each step
   (parse + validate the body, build the frame and score, build the response objects, serialise to JSON).
   Median over --repeat runs after a warm-up.
2. **cProfile** of complete requests through FastAPI's TestClient, top functions by own time.
The span numbers exclude HTTP parsing, the event loop and the thread hand-off that FastAPI adds;
compare them with the end-to-end time printed at the end to see how much that is.
"""
from __future__ import annotations

import argparse
import cProfile
import io
import pstats
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "src"))

import pandas as pd  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from flowguard.api import create_app  # noqa: E402
from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import SENSOR_COLUMNS  # noqa: E402
from flowguard.schemas import PredictRequest, PredictResponse, SampleResult  # noqa: E402
from measure_service import MODEL_DIR, request_body  # noqa: E402


def spans(body: bytes, detector) -> dict[str, float]:
    t = [time.perf_counter()]
    req = PredictRequest.model_validate_json(body)
    t.append(time.perf_counter())
    frame = pd.DataFrame([s.model_dump() for s in req.samples]).rename(columns={"timestamp": "datetime"})
    scores = detector.score_batch(frame[["datetime", *SENSOR_COLUMNS]])
    t.append(time.perf_counter())
    results = [SampleResult(timestamp=s.timestamp, score=None if pd.isna(x) else float(x),
                            status="warming_up" if pd.isna(x) else "ok",
                            exceeds_threshold=None if pd.isna(x) else bool(x >= detector.threshold))
               for s, x in zip(req.samples, scores, strict=True)]
    resp = PredictResponse(request_id="x", model_version=detector.version, machine_id=req.machine_id,
                           threshold=detector.threshold, n_samples=len(results), results=results)
    t.append(time.perf_counter())
    resp.model_dump_json()
    t.append(time.perf_counter())
    names = ["parse + validate request", "build frame + score", "build response objects", "serialise response"]
    return {n: 1000 * (b - a) for n, a, b in zip(names, t[:-1], t[1:], strict=True)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--batch", type=int, default=600)
    ap.add_argument("--repeat", type=int, default=50)
    args = ap.parse_args(argv)
    body, source = request_body(args.batch)
    detector, _ = load_bundle(MODEL_DIR)
    for _ in range(5):
        spans(body, detector)
    runs = [spans(body, detector) for _ in range(args.repeat)]
    print(f"request: {source}, {len(body) / 1024:.0f} KiB of JSON\n\nspan medians over {args.repeat} runs:")
    total = 0.0
    for name in runs[0]:
        med = statistics.median(r[name] for r in runs)
        total += med
        print(f"  {name:<28} {med:7.2f} ms")
    print(f"  {'sum of spans':<28} {total:7.2f} ms")
    with TestClient(create_app(MODEL_DIR)) as client:
        for _ in range(5):
            client.post("/predict", content=body, headers={"Content-Type": "application/json"})
        e2e = []
        prof = cProfile.Profile()
        for _ in range(args.repeat):
            start = time.perf_counter()
            prof.enable()
            client.post("/predict", content=body, headers={"Content-Type": "application/json"})
            prof.disable()
            e2e.append(1000 * (time.perf_counter() - start))
    print(f"\nend-to-end through TestClient (median, profiler on): {statistics.median(e2e):.2f} ms\n")
    out = io.StringIO()
    pstats.Stats(prof, stream=out).sort_stats("tottime").print_stats(12)
    print("\n".join(line for line in out.getvalue().splitlines() if line.strip())[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
