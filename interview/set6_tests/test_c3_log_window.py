"""C3: behaviour from the specification in interview/set6_debugging.md (not one implementation)."""
import json
import random

import numpy as np
import pytest

END = "2026-03-10T10:05:00+00:00"


def req(ts, path="/predict", status=200, ms=10.0, **extra):
    rec = {"ts": ts, "level": "INFO", "event": "request", "path": path, "status": status,
           "duration_ms": ms}
    rec.update(extra)
    return json.dumps(rec)


def at(seconds_before_end):
    """ISO timestamp `seconds_before_end` seconds before END (UTC)."""
    from datetime import datetime, timedelta
    t = datetime.fromisoformat(END) - timedelta(seconds=seconds_before_end)
    return t.isoformat()


def summary(c3, lines, **kw):
    return c3.window_summary(lines, END, **kw)


def test_single_endpoint_counts_and_p95(c3):
    lines = [req(at(i), ms=float(i + 1)) for i in range(20)]        # durations 1..20
    s = summary(c3, lines)
    e = s["endpoints"]["/predict"]
    assert e["count"] == 20
    assert e["error_rate"] == 0.0
    assert e["p95_ms"] == pytest.approx(float(np.percentile(np.arange(1, 21), 95)))   # 19.05
    assert s["skipped"] == 0


def test_p95_uses_linear_interpolation_on_random_data(c3):
    rng = random.Random(3)
    ms = [round(rng.lognormvariate(2.5, 0.6), 3) for _ in range(137)]
    lines = [req(at(i % 290), ms=m) for i, m in enumerate(ms)]
    e = summary(c3, lines)["endpoints"]["/predict"]
    assert e["p95_ms"] == pytest.approx(float(np.percentile(ms, 95)), rel=1e-9)


def test_endpoints_are_separate_and_query_strings_are_stripped(c3):
    lines = [req(at(10), path="/predict?batch=1", ms=5), req(at(20), path="/predict", ms=7),
             req(at(30), path="/readyz", ms=1)]
    eps = summary(c3, lines)["endpoints"]
    assert set(eps) == {"/predict", "/readyz"}
    assert eps["/predict"]["count"] == 2 and eps["/readyz"]["count"] == 1


def test_window_bounds_exclude_start_include_end(c3):
    lines = [req(at(0), ms=1), req(at(299.999), ms=2), req(at(300), ms=3), req(at(-1), ms=4)]
    e = summary(c3, lines)["endpoints"]["/predict"]
    assert e["count"] == 2           # exactly at end and just inside; not at end - 300 s, not after end


def test_lines_out_of_order_are_all_considered(c3):
    lines = [req(at(400), ms=1), req(at(10), ms=2), req(at(500), ms=3), req(at(20), ms=4)]
    assert summary(c3, lines)["endpoints"]["/predict"]["count"] == 2


def test_window_length_parameter(c3):
    lines = [req(at(s)) for s in (5, 50, 500)]
    assert summary(c3, lines, window_s=60)["endpoints"]["/predict"]["count"] == 2
    assert summary(c3, lines, window_s=1000)["endpoints"]["/predict"]["count"] == 3


def test_timezone_offsets_are_respected(c3):
    # END is 10:05:00Z. 11:04:30+01:00 and 09:04:30-01:00 are both 10:04:30Z: inside.
    # 10:04:30+02:00 is 08:04:30Z: two hours before the end, outside, although its wall clock looks close.
    lines = [req("2026-03-10T11:04:30+01:00"), req("2026-03-10T09:04:30-01:00"),
             req("2026-03-10T10:04:30+02:00")]
    assert summary(c3, lines)["endpoints"]["/predict"]["count"] == 2


def test_error_rate_counts_5xx_over_all_requests(c3):
    lines = ([req(at(i), status=200) for i in range(6)] + [req(at(10 + i), status=503) for i in range(2)]
             + [req(at(20 + i), status=422) for i in range(2)])
    e = summary(c3, lines)["endpoints"]["/predict"]
    assert e["count"] == 10
    assert e["error_rate"] == pytest.approx(0.2)       # 4xx are client errors, not service errors


def test_p95_over_2xx_only(c3):
    ok = [req(at(i), status=200, ms=10.0) for i in range(19)]
    bad = [req(at(100), status=500, ms=10_000.0), req(at(101), status=422, ms=0.5)]
    e = summary(c3, ok + bad)["endpoints"]["/predict"]
    assert e["p95_ms"] == pytest.approx(10.0)


def test_endpoint_with_no_success_has_p95_none(c3):
    lines = [req(at(1), path="/predict", status=503, ms=2.0), req(at(2), path="/predict", status=500)]
    e = summary(c3, lines)["endpoints"]["/predict"]
    assert e["p95_ms"] is None and e["error_rate"] == 1.0 and e["count"] == 2


def test_malformed_lines_are_counted_not_fatal(c3):
    lines = [req(at(1)),
             "not json at all",
             json.dumps(["a", "list"]),
             json.dumps({"event": "request", "path": "/predict", "status": 200}),        # no ts, no duration
             req("2026-03-10T10:04:00", ms=3),                                          # naive timestamp
             req(at(2), status="200"),                                                  # status as a string
             req(at(3), ms=float("nan")),                                               # NaN duration (json writes NaN)
             ""]                                                                         # blank: ignored
    s = summary(c3, lines)
    assert s["endpoints"]["/predict"]["count"] == 1
    assert s["skipped"] == 6


def test_other_events_are_ignored_not_skipped(c3):
    lines = [req(at(1)),
             json.dumps({"ts": at(2), "level": "INFO", "event": "model_loaded", "version": "1.0.0"}),
             json.dumps({"ts": at(3), "level": "ERROR", "event": "model_not_loaded", "msg": "checksum"})]
    s = summary(c3, lines)
    assert s["skipped"] == 0 and s["endpoints"]["/predict"]["count"] == 1


def test_empty_input(c3):
    assert summary(c3, []) == {"endpoints": {}, "skipped": 0}


def test_accepts_a_generator_read_once(c3):
    def gen():
        for i in range(5):
            yield req(at(i))
    assert summary(c3, gen())["endpoints"]["/predict"]["count"] == 5


def test_result_is_plain_and_json_serialisable(c3):
    s = summary(c3, [req(at(1)), req(at(2), path="/readyz")])
    json.dumps(s)
    assert set(s["endpoints"]["/predict"]) == {"count", "error_rate", "p95_ms"}
