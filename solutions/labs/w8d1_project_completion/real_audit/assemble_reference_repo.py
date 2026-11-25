"""Assemble a throwaway git repository holding the reference flowguard evaluation (w4d6), so the
clean-clone audit can be run against it for real.

    python solutions/labs/w8d1_project_completion/real_audit/assemble_reference_repo.py <empty dir>
    python solutions/labs/w8d1_project_completion/lab/audit/clean_clone_check.py <that dir> \
        --log solutions/labs/w8d1_project_completion/real_audit/REPRODUCTION_LOG.md

What goes in: the w4d6 reference lab (Makefile, src/, splits/v2.json), the data download script with its
pinned commit and hashes (project/get_skab.py, unchanged), a fully pinned requirements.lock (the output
of `pip freeze` in a venv holding the versions recorded in the report's provenance), REPRODUCE.toml,
and the committed reference results as expected/results.json. The raw data is NOT committed: the first
audit step downloads it, as a clean clone must.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
W4D6 = ROOT / "solutions" / "labs" / "w4d6_project_milestone_1"

LOCK = """\
# Fully pinned: direct AND transitive dependencies (pip freeze, 2026-11-22, Python 3.13)
cloudpickle==3.1.3
joblib==1.6.0
narwhals==2.29.0
numpy==2.5.3
pandas==3.0.5
python-dateutil==4.0.0
scikit-learn==1.9.1
scipy==1.18.1
threadpoolctl==3.8.0
tzdata==2026.6
"""

REPRODUCE = """\
# How to reproduce the headline numbers of reports/evaluation.md from a clean clone.
[environment]
requirements = "requirements.lock"

[[step]]
name = "download data (pinned commit, SHA-256 per file)"
run = ["python", "scripts/get_skab.py"]
timeout_s = 600

[[step]]
name = "verify data hashes"
run = ["python", "scripts/get_skab.py", "--verify"]
timeout_s = 120

[[step]]
name = "evaluate (ingest, evaluate, report)"
run = ["make", "evaluate"]
timeout_s = 1800

[headline]
produced = "results/results.json"
expected = "expected/results.json"
repeat = 1
"""

KEYS = ["data.rows", "data.experiments", "decision.chosen",
        "development.0.primary", "development.0.primary_lo", "development.0.primary_hi",
        "development.3.diff", "development.3.diff_lo", "development.3.diff_hi",
        "test.0.name", "test.0.pr_auc", "test.0.pr_auc_lo", "test.0.pr_auc_hi",
        "test.0.events_detected", "test.0.events_total", "test.0.median_delay_s",
        "test.3.pr_auc", "test.3.events_detected"]


def main() -> int:
    dest = Path(sys.argv[1]).resolve()
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"{dest} is not empty")
    dest.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.egg-info", "data", "results", "reports")
    for name in ("Makefile", "pyproject.toml"):
        shutil.copy2(W4D6 / "lab" / name, dest / name)
    for name in ("src", "splits"):
        shutil.copytree(W4D6 / "lab" / name, dest / name, ignore=ignore)
    (dest / "scripts").mkdir()
    shutil.copy2(ROOT / "project" / "get_skab.py", dest / "scripts" / "get_skab.py")
    (dest / "expected").mkdir()
    shutil.copy2(W4D6 / "example_report" / "results.json", dest / "expected" / "results.json")
    (dest / "requirements.lock").write_text(LOCK)
    values = "".join(f'\n[[headline.value]]\nkey = "{k}"\nabs_tol = 1e-9\n' for k in KEYS)
    (dest / "REPRODUCE.toml").write_text(REPRODUCE + values)
    (dest / ".gitignore").write_text("data/\nresults/\nreports/\n__pycache__/\n")
    git = ["git", "-c", "user.name=auditor", "-c", "user.email=auditor@example.invalid"]
    subprocess.run(["git", "init", "--quiet"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(git + ["commit", "--quiet", "-m", "reference flowguard evaluation (w4d6)"], cwd=dest, check=True)
    print(f"assembled {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
