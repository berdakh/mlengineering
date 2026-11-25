"""Regenerate the data figure of lesson w5d2 and print its numbers.

    python project/get_skab.py                                          # once
    python labs/w5d2_artifacts_versioning/figures/make_figures.py    # about 30 seconds

REAL SKAB: both models are trained on the 27 development experiments of the frozen manifest v2
(the flow-rate detector's operating point and the supervised logistic candidate, as in w4d5/w5d1).
Each is serialised three ways where that applies; size on disk and median load time over 200 loads
are measured. Load times depend on the machine; the relative picture is what matters.
matplotlib is needed only here. Pass --png DIR for PNG copies.
"""
from __future__ import annotations

import argparse
import pickle
import shutil
import sys
import tempfile
import time
from pathlib import Path

import joblib
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REF = ROOT / "solutions" / "labs" / "w5d2_artifacts_versioning"
sys.path[:0] = [str(ROOT), str(REF / "challenge"), str(REF / "lab"), str(REF / "lab" / "src")]

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from build_model import build  # noqa: E402
from logistic_bundle import load_logistic, save_logistic  # noqa: E402

from flowguard.artifacts import load_bundle, save_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.detectors import SupervisedLogistic  # noqa: E402
from flowguard.inference import Detector  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

META = {"intended_use": "measurement", "limitations": ["measurement only"], "training_data": {"x": 1},
        "evaluation": {"x": 1}, "code_version": "measurement"}


def size(path: Path) -> int:
    return path.stat().st_size if path.is_file() else sum(p.stat().st_size for p in path.iterdir())


def load_ms(fn, n=200) -> float:
    fn()
    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    return 1000 * float(np.median(times))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", default=None)
    args = ap.parse_args()
    raw = ROOT / "data" / "raw" / "skab"
    tidy = load_raw(raw)
    manifest = load_splits(REF / "lab" / "splits" / "v2.json")
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))]
    flow = Detector.from_config(build(raw))
    logistic = SupervisedLogistic(n_burn=100).fit(dev)

    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for label, obj in (("flow-rate detector", flow), ("logistic candidate", logistic)):
            p = tmp / f"{label}.pkl"
            p.write_bytes(pickle.dumps(obj, protocol=5))
            rows.append((label, "pickle", size(p), load_ms(lambda p=p: pickle.loads(p.read_bytes()))))
            j = tmp / f"{label}.joblib"
            joblib.dump(obj, j)
            rows.append((label, "joblib", size(j), load_ms(lambda j=j: joblib.load(j))))
        b1 = save_bundle(flow, tmp / "flow-bundle", META, {"x": np.arange(27.0), "y": np.arange(27.0)})
        rows.append(("flow-rate detector", "JSON + npz bundle\n(checksums verified)", size(b1), load_ms(lambda: load_bundle(b1))))
        b2 = save_logistic(logistic, tmp / "logistic-bundle", META, version="0.1.0")
        rows.append(("logistic candidate", "JSON + npz bundle\n(checksums verified)", size(b2), load_ms(lambda: load_logistic(b2))))

    for r in rows:
        print(f"  {r[0]:<20} {r[1].splitlines()[0]:<18} {r[2]:>7,} B   load {r[3]:.3f} ms")
    fmts = ["pickle", "joblib", "JSON + npz bundle\n(checksums verified)"]
    models = ["flow-rate detector", "logistic candidate"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.6, 3.4))
    width = 0.38
    x = np.arange(len(fmts))
    for k, model in enumerate(models):
        vals = {r[1]: r for r in rows if r[0] == model}
        sizes = [vals[f][2] for f in fmts]
        times = [vals[f][3] for f in fmts]
        a1.bar(x + (k - 0.5) * width, sizes, width * 0.95, color=SERIES[k], label=model)
        a2.bar(x + (k - 0.5) * width, times, width * 0.95, color=SERIES[k], label=model)
        for xi, v in zip(x + (k - 0.5) * width, sizes):
            a1.text(xi, v, f"{v:,}", ha="center", va="bottom", fontsize=8, color=INK["secondary"])
    for ax, title, ylabel in ((a1, "size on disk", "bytes"), (a2, "median load time", "milliseconds")):
        ax.set_xticks(x, [f.replace(" bundle", "\nbundle").split("\n(")[0] for f in fmts], fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylabel)
        ax.grid(axis="x", visible=False)
    a1.legend(loc="upper left")
    fig.suptitle("Real SKAB models: a safe bundle costs a few kilobytes and well under a millisecond to load",
                 x=0.01, y=1.04, ha="left", fontweight="bold", fontsize=11)
    if args.png:
        Path(args.png).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(args.png) / "formats.png", dpi=110)
    save(fig, HERE / "formats.svg")
    print("wrote formats.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
