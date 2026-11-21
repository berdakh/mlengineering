"""Optional end-to-end proof: a fresh venv, a real `pip install -e`, the console script.

Skipped by default because it downloads the dependencies (about a minute, needs network):

    WB_RUN_SLOW=1 python -m pytest lessons/w1d3_package_structure/checks/test_real_install.py -q
"""
import json
import os
import subprocess
import sys

import pytest


@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("WB_RUN_SLOW") != "1", reason="set WB_RUN_SLOW=1 to run the real-install check")
def test_editable_install_exposes_console_script(target, data_csv, tmp_path):
    venv = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = subprocess.run(
        [str(venv / "bin" / "python"), "-m", "pip", "install", "-q", "-e", str(target)],
        capture_output=True, text=True,
    )
    assert pip.returncode == 0, pip.stderr[-1500:]
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    proc = subprocess.run(
        [str(venv / "bin" / "pumpwatch"), "train", "--data", str(data_csv)],
        cwd=cwd, capture_output=True, text=True, env={"PATH": os.environ.get("PATH", "")},
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    assert json.loads(proc.stdout)["auc"] == pytest.approx(0.9992283950617284, abs=1e-6)
