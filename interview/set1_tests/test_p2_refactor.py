import json
import subprocess
import sys
from datetime import datetime, timedelta

import pytest

from conftest import load

NOW = datetime(2021, 3, 10, 12, 0, 0)     # deliberately far from the real clock


@pytest.fixture(scope="module")
def p2():
    return load("p2")


def ev(delta_hours, level, message="m"):
    return {"ts": NOW - timedelta(hours=delta_hours), "level": level, "message": message}


def test_import_has_no_side_effects(target_dir):
    code = (
        "import builtins, importlib.util, sys\n"
        "real_open = builtins.open\n"
        "def guarded(file, *a, **k):\n"
        "    if str(file).endswith('p2.py') or 'pycache' in str(file): return real_open(file, *a, **k)\n"
        "    raise AssertionError(f'import opened {file}')\n"
        "spec = importlib.util.spec_from_file_location('p2', sys.argv[1])\n"
        "m = importlib.util.module_from_spec(spec)\n"
        "builtins.open = guarded\n"
        "spec.loader.exec_module(m)\n"
    )
    proc = subprocess.run([sys.executable, "-c", code, str(target_dir / "p2.py")], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-800:]
    assert proc.stdout == "", "importing the module printed something"


def test_parse_line_well_formed(p2):
    out = p2.parse_line("2026-11-20T09:15:00 ERROR disk full on /dev/sda1\n")
    assert out == {"ts": datetime(2026, 11, 20, 9, 15), "level": "ERROR", "message": "disk full on /dev/sda1"}


@pytest.mark.parametrize("line", ["", "\n", "not-a-date ERROR x", "2026-11-20T09:15:00", "2026-11-20T09:15:00 INFO"])
def test_parse_line_malformed_returns_none(p2, line):
    assert p2.parse_line(line) is None


def test_summarize_uses_the_now_argument_not_the_clock(p2):
    out = p2.summarize([ev(1, "INFO"), ev(2, "ERROR", "boom")], NOW)
    assert out == {"counts": {"INFO": 1, "ERROR": 1}, "last_error": "boom"}


def test_window_is_open_at_24h_and_closed_at_now(p2):
    events = [
        ev(24, "INFO"),                                   # exactly 24 h old: outside
        ev(23.999, "WARNING"),                            # just inside
        ev(0, "ERROR", "at now"),                         # exactly now: inside
        {"ts": NOW + timedelta(seconds=1), "level": "ERROR", "message": "future"},   # after now: outside
        ev(30, "ERROR", "old"),
    ]
    out = p2.summarize(events, NOW)
    assert out["counts"] == {"WARNING": 1, "ERROR": 1}
    assert out["last_error"] == "at now"


def test_last_error_is_most_recent_regardless_of_input_order(p2):
    events = [ev(1, "ERROR", "newer"), ev(5, "ERROR", "older"), ev(3, "INFO")]
    assert p2.summarize(events, NOW)["last_error"] == "newer"
    assert p2.summarize(list(reversed(events)), NOW)["last_error"] == "newer"


def test_no_events_and_no_errors(p2):
    assert p2.summarize([], NOW) == {"counts": {}, "last_error": None}
    assert p2.summarize([ev(1, "INFO")], NOW) == {"counts": {"INFO": 1}, "last_error": None}


def test_summarize_does_not_mutate_input(p2):
    events = [ev(1, "INFO"), ev(2, "ERROR", "x")]
    snapshot = [dict(e) for e in events]
    p2.summarize(events, NOW)
    assert events == snapshot


def test_main_prints_one_json_line(p2, tmp_path, capsys):
    recent = (datetime.now() - timedelta(hours=1)).replace(microsecond=0).isoformat()
    old = (datetime.now() - timedelta(days=3)).replace(microsecond=0).isoformat()
    log = tmp_path / "events.log"
    log.write_text(f"{recent} ERROR pump offline\n\ngarbage line\n{old} ERROR ancient\n{recent} INFO ok\n")
    assert p2.main([str(log)]) == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    assert json.loads(out[0]) == {"counts": {"ERROR": 1, "INFO": 1}, "last_error": "pump offline"}


def test_main_missing_file_returns_2(p2, tmp_path, capsys):
    assert p2.main([str(tmp_path / "nope.log")]) == 2
    assert capsys.readouterr().out == ""
