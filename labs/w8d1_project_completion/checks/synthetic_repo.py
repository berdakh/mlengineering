"""SYNTHETIC repositories for the w8d1 checks: a tiny stdlib-only project, plus variants that each carry
one reproduction defect. Nothing here says anything about SKAB; it exercises the audit tool only.

Every variant is a real git repository with one commit, created in a temporary directory.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

READINGS = "\n".join(["unit,score,label"] + [f"u{i % 5},{(i * 37 % 101) / 101:.4f},{int(i % 3 == 0)}"
                                              for i in range(60)]) + "\n"

PIPELINE = '''"""toyproj: computes headline numbers from data/readings.csv (SYNTHETIC)."""
import json
import pathlib
import sys

DATA = pathlib.Path(%(data)r)


def main():
    rows = [line.split(",") for line in DATA.read_text().splitlines()[1:]]
    scores = [float(r[1]) for r in rows]
    labels = [int(r[2]) for r in rows]
    %(extra)s
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    out = {"rows": len(rows), "test": {"auc": round(wins / (len(pos) * len(neg)), 10),
           "positives": len(pos)}}
    path = pathlib.Path("results/headline.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(out, indent=2, sort_keys=True))
    print("wrote", path)


if __name__ == "__main__":
    sys.exit(main())
'''

REPRODUCE = '''[environment]
requirements = "requirements.lock"

[[step]]
name = "evaluate"
run = ["python", "-m", "toyproj"]
timeout_s = 60

[headline]
produced = "results/headline.json"
expected = "expected/headline.json"
repeat = %(repeat)d

[[headline.value]]
key = "rows"
abs_tol = 0

[[headline.value]]
key = "test.auc"
abs_tol = 1e-9

[[headline.value]]
key = "test.positives"
abs_tol = 0
'''

VARIANTS = ("good", "absolute_path", "unpinned", "missing_dependency", "hand_edited", "untracked_data",
            "nondeterministic")


def true_headline() -> dict:
    rows = [line.split(",") for line in READINGS.splitlines()[1:]]
    scores = [float(r[1]) for r in rows]
    labels = [int(r[2]) for r in rows]
    pos = [s for s, y in zip(scores, labels) if y == 1]
    neg = [s for s, y in zip(scores, labels) if y == 0]
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return {"rows": len(rows), "test": {"auc": round(wins / (len(pos) * len(neg)), 10), "positives": len(pos)}}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=synthetic", "-c", "user.email=synthetic@example.invalid", *args],
                   cwd=repo, check=True, capture_output=True)


def make_repo(root: Path, variant: str) -> Path:
    """Create the variant under root/<variant> and return its path."""
    assert variant in VARIANTS, variant
    repo = root / variant
    (repo / "toyproj").mkdir(parents=True)
    (repo / "data").mkdir()
    (repo / "expected").mkdir()
    data, extra, lock, repeat = "data/readings.csv", "", "# stdlib only: nothing to install\n", 1
    expected = true_headline()
    if variant == "absolute_path":
        data = "/home/alice/flowguard/data/readings.csv"
    elif variant == "unpinned":
        lock = "# direct dependencies\nrequests>=2.31\n"
    elif variant == "missing_dependency":
        extra = "import numpy  # used but never declared\n    scores = [float(x) for x in numpy.asarray(scores)]"
    elif variant == "hand_edited":
        expected["test"]["auc"] = round(expected["test"]["auc"] + 0.031, 10)  # "rounded up" in the report
    elif variant == "nondeterministic":
        extra = "import random\n    rows = random.sample(rows, 45)  # unseeded subsample"
        scores_note = None  # noqa: F841
        repeat = 2
    if variant == "good":
        repeat = 2
    (repo / "toyproj" / "__init__.py").write_text("")
    (repo / "toyproj" / "__main__.py").write_text(PIPELINE % {"data": data, "extra": extra})
    if variant == "nondeterministic":
        # the subsample happens before scores and labels are read from rows
        src = (repo / "toyproj" / "__main__.py").read_text()
        src = src.replace('    rows = [line.split(",") for line in DATA.read_text().splitlines()[1:]]\n'
                          '    scores = [float(r[1]) for r in rows]\n    labels = [int(r[2]) for r in rows]\n'
                          '    import random\n    rows = random.sample(rows, 45)  # unseeded subsample\n',
                          '    rows = [line.split(",") for line in DATA.read_text().splitlines()[1:]]\n'
                          '    import random\n    rows = random.sample(rows, 45)  # unseeded subsample\n'
                          '    scores = [float(r[1]) for r in rows]\n    labels = [int(r[2]) for r in rows]\n')
        (repo / "toyproj" / "__main__.py").write_text(src)
    (repo / "data" / "readings.csv").write_text(READINGS)
    (repo / "requirements.lock").write_text(lock)
    (repo / "REPRODUCE.toml").write_text(REPRODUCE % {"repeat": repeat})
    (repo / "expected" / "headline.json").write_text(json.dumps(expected, indent=2, sort_keys=True))
    ignore = "results/\n__pycache__/\n" + ("data/\n" if variant == "untracked_data" else "")
    (repo / ".gitignore").write_text(ignore)
    _git(repo, "init", "--quiet")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", f"synthetic {variant} project")
    return repo
