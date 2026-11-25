"""flowguard.logquery and `python -m flowguard.cli logs`."""
from __future__ import annotations

import json
import os
import subprocess
import sys

LINES = [
    json.dumps({"ts": "t1", "event": "prediction", "request_id": "A", "n_samples": 5}),
    "uvicorn text line that is not JSON",
    json.dumps({"ts": "t2", "event": "access", "request_id": "B", "status": 200}),
    json.dumps([1, 2, 3]),
    "",
    json.dumps({"ts": "t3", "event": "access", "request_id": "A", "status": 200, "route": "/predict"}),
    "{truncated json",
]


def test_find_request_keeps_order_and_skips_junk(fg):
    res = fg["logquery"].find_request(iter(LINES), "A")
    assert [e["ts"] for e in res.events] == ["t1", "t3"]
    assert res.skipped_lines == 3, f"expected 3 skipped non-JSON-object lines, got {res.skipped_lines}"
    assert fg["logquery"].find_request(iter(LINES), "Z").events == []


def _cli(target, tmp_path, *args):
    env = dict(os.environ, PYTHONPATH=str(target / "src"))
    return subprocess.run([sys.executable, "-m", "flowguard.cli", "logs", *args],
                          capture_output=True, text=True, env=env, cwd=tmp_path, timeout=60)


def test_cli_exit_codes(target, tmp_path):
    log = tmp_path / "service.log"
    log.write_text("\n".join(LINES) + "\n")
    found = _cli(target, tmp_path, "--file", str(log), "--request-id", "A")
    assert found.returncode == 0, found.stderr
    assert "A" in found.stdout and "200" in found.stdout
    missing = _cli(target, tmp_path, "--file", str(log), "--request-id", "nope")
    assert missing.returncode == 1
    unreadable = _cli(target, tmp_path, "--file", str(tmp_path / "absent.log"), "--request-id", "A")
    assert unreadable.returncode == 2
