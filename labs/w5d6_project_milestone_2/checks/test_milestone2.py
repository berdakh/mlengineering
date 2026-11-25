"""Release-candidate checks for milestone 2 (synthetic project; see conftest.py)."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tomllib

import pandas as pd

from conftest import env_for, make

TOL = 1e-9


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_make_model_builds_a_bundle(project, built):
    assert built.returncode == 0, "make model failed:\n" + built.stdout[-1500:] + built.stderr[-1500:]
    for name in ("model.json", "MANIFEST.json"):
        assert (project / "models" / "current" / name).is_file(), f"make model must write models/current/{name}"


def test_bundle_records_provenance(project, built):
    manifest = json.loads((project / "models" / "current" / "MANIFEST.json").read_text())
    prov = manifest.get("provenance", {})
    assert prov.get("splits_sha256") == sha256(project / "splits" / "v2.json"), \
        "the bundle must record the sha256 of the split manifest it was built from"
    assert prov.get("config_sha256") == sha256(project / "configs" / "model.toml"), \
        "the bundle must record the sha256 of configs/model.toml"


def test_make_test_passes(project, built):
    tests = "\n".join(p.read_text() for p in (project / "tests").rglob("test_*.py"))
    assert "TestClient" in tests, "tests/ needs API tests (TestClient)"
    assert re.search(r"parity|predict-batch|score_experiments", tests), "tests/ needs a parity test"
    proc = make(project, "test")
    assert proc.returncode == 0, "make test failed:\n" + proc.stdout[-2000:] + proc.stderr[-1000:]
    assert re.search(r"\d+ passed", proc.stdout), "make test should run pytest and report passed tests"


def test_three_way_parity(probe):
    assert probe["batch_ok"], "predict-batch --split all failed:\n" + probe["batch_stderr"]
    assert probe["eval_vs_batch"] is not None and probe["eval_vs_batch"] <= TOL, \
        f"evaluation and batch scores differ (max |diff| {probe['eval_vs_batch']})"
    assert probe["eval_vs_api"] is not None and probe["eval_vs_api"] <= TOL, \
        f"evaluation and API scores differ (max |diff| {probe['eval_vs_api']}): training/serving skew"


def test_batch_output_contract(project, built):
    out = project / "predictions" / "check_test.csv"
    proc = subprocess.run([sys.executable, "-m", "flowguard", "predict-batch", "--model", "models/current",
                           "--raw", "data/raw/skab", "--splits", "splits/v2.json", "--split", "test",
                           "--out", str(out)], cwd=project, capture_output=True, text=True, env=env_for(project))
    assert proc.returncode == 0, proc.stderr[-1500:]
    frame = pd.read_csv(out)
    assert list(frame.columns) == ["experiment_id", "t", "score", "above_threshold"]
    test_ids = json.loads((project / "splits" / "v2.json").read_text())["test"]
    assert sorted(frame["experiment_id"].unique()) == sorted(test_ids)


def test_bad_model_dir_is_a_clean_error(project, built):
    proc = subprocess.run([sys.executable, "-m", "flowguard", "predict-batch", "--model", "models/missing",
                           "--raw", "data/raw/skab", "--out", "predictions/x.csv"],
                          cwd=project, capture_output=True, text=True, env=env_for(project))
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr, "a missing bundle should give a one-line error, not a traceback"


def test_versions_agree(project, probe):
    version = probe["package_version"]
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())["project"]
    if "version" in pyproject:
        assert pyproject["version"] == version, \
            f"pyproject.toml says {pyproject['version']}, flowguard.__version__ says {version}"
    else:
        attr = tomllib.loads((project / "pyproject.toml").read_text()).get("tool", {}).get("setuptools", {}) \
            .get("dynamic", {}).get("version", {}).get("attr")
        assert attr == "flowguard.__version__", "dynamic version must come from flowguard.__version__"
    bundle = json.loads((project / "models" / "current" / "MANIFEST.json").read_text())["package_version"]
    assert bundle == version, f"bundle records {bundle}, package is {version}"
    assert probe["api_version"] == version, f"/version reports {probe['api_version']}, package is {version}"


def test_changelog_has_entry(project, probe):
    text = (project / "CHANGELOG.md").read_text()
    assert re.search(rf"^## \[{re.escape(probe['package_version'])}\]", text, flags=re.M), \
        f"CHANGELOG.md needs a '## [{probe['package_version']}]' section"


def test_readme_usage_commands_run(project, built):
    text = (project / "README.md").read_text()
    assert "## Usage" in text, "README.md needs a '## Usage' section"
    usage = text.split("## Usage", 1)[1].split("\n## ", 1)[0]
    block = re.search(r"```(?:bash|sh)\n(.*?)```", usage, flags=re.S)
    assert block, "the Usage section needs a ```bash code block"
    lines = [ln.strip() for ln in block.group(1).splitlines() if ln.strip() and not ln.strip().startswith("#")]
    assert any(ln.startswith("curl") and "/predict" in ln for ln in lines), "show a curl call to /predict"
    runnable = [ln for ln in lines if not ln.startswith("curl") and "serve" not in ln and "uvicorn" not in ln]
    assert len(runnable) >= 3, "the Usage block should contain at least three runnable commands"
    for line in runnable:
        proc = subprocess.run(["bash", "-c", line], cwd=project, capture_output=True, text=True,
                              env=env_for(project), timeout=300)
        assert proc.returncode == 0, f"README command failed: {line}\n{proc.stderr[-1000:]}"
