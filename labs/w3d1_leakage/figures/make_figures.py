"""Regenerate the figures of lesson w3d1 (about 4 minutes; most of it is the pure-noise simulation).

    python labs/w3d1_leakage/figures/make_figures.py            # SVGs next to this file
    python labs/w3d1_leakage/figures/make_figures.py --png DIR  # also PNG copies, for checking

The invoice figure names the planted leaks, so it is written to solutions/labs/w3d1_leakage/figures/.
Figures 1 and 2 use the SYNTHETIC invoice export and pure-noise data; figure 3 uses the REAL SKAB files
(`python project/get_skab.py` first; skipped with a message if they are absent). Every number drawn is
also printed. matplotlib is an authoring dependency only; no lab or check imports it.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

HONEST, LEAKY = SERIES[0], SERIES[1]          # in this lesson "honest" is always SERIES[0], "leaky" SERIES[1]
PNG_DIR: Path | None = None


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SOLUTION_FIGURES = ROOT / "solutions" / "labs" / "w3d1_leakage" / "figures"   # figures that reveal answers


def out(fig, name: str, directory: Path = HERE) -> None:
    if PNG_DIR is not None:
        fig.savefig(PNG_DIR / f"{name}.png", dpi=110)
    save(fig, directory / f"{name}.svg")


# ---------------------------------------------------------------- 1. invoice leaks, one at a time
def fig_invoice_leaks() -> None:
    from sklearn.metrics import average_precision_score
    from sklearn.model_selection import train_test_split

    honest = load(ROOT / "solutions" / "labs" / "w3d1_leakage" / "lab" / "leakhunt" / "honest_eval.py", "honest")
    gen = load(UNIT / "data" / "make_invoices.py", "make_invoices")
    export, production = gen.simulate(gen.SEED)
    public, prod = gen.public_view(export), gen.public_view(production)

    def run(keep=(), dedupe=True, random=False) -> float:
        df = public.sort_values(["issue_date", "invoice_id"], kind="stable")
        if dedupe:
            df = df.drop_duplicates(subset=honest.REISSUE_KEY, keep="first")
        df = df.drop(columns=[c for c in honest.LEAKY_COLUMNS if c not in keep]).reset_index(drop=True)
        if random:
            train, test = train_test_split(df, test_size=0.2, random_state=0, stratify=df["paid_late"])
        else:
            train, test = honest.split(df)
        saved = honest.NUMERIC[:]
        honest.NUMERIC[:] = saved + list(keep)
        features = honest.FEATURES + list(keep)
        model = honest.build_model().fit(train[features], train["paid_late"])
        honest.NUMERIC[:] = saved
        return float(average_precision_score(test["paid_late"], model.predict_proba(test[features])[:, 1]))

    result = honest.evaluate(public.copy())
    production_ap = float(average_precision_score(prod["paid_late"], result["model"].predict_proba(prod)[:, 1]))
    rows = [
        ("honest: all five fixes", run()),
        ("+ keep re-issued duplicates", run(dedupe=False)),
        ("+ keep customer_late_rate", run(keep=("customer_late_rate",))),
        ("+ random split instead of time", run(random=True)),
        ("+ keep ledger_ref", run(keep=("ledger_ref",))),
        ("+ keep reminders_sent", run(keep=("reminders_sent",))),
        ("inherited script: everything leaky", run(keep=tuple(honest.LEAKY_COLUMNS), dedupe=False, random=True)),
    ]
    for name, value in rows:
        print(f"invoice_leaks: {name:40s} {value:.3f}")
    print(f"invoice_leaks: production-like rows (later invoices, issue-time view) {production_ap:.3f}; "
          f"prevalence {prod['paid_late'].mean():.3f}")

    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    names = [r[0] for r in rows][::-1]
    values = [r[1] for r in rows][::-1]
    colours = [HONEST if n.startswith("honest") else LEAKY for n in names]
    ax.barh(names, values, color=colours, height=0.6)
    for y, v in enumerate(values):
        ax.text(v + 0.01, y, f"{v:.3f}", va="center", fontsize=9, color=INK["secondary"])
    ax.axvline(production_ap, color=INK["primary"], linestyle="--", linewidth=1.5)
    ax.text(production_ap + 0.01, -0.75, f"dashed line: AP on later invoices, as served = {production_ap:.3f}",
            fontsize=9, color=INK["primary"], va="center")
    ax.set_ylim(-1.1, len(values) - 0.4)
    ax.set_xlim(0, 1.12)
    ax.set_xlabel("test average precision (higher looks better)")
    ax.set_title("Each leak alone inflates the estimate; only the honest one predicts production (SYNTHETIC)")
    ax.grid(axis="y", visible=False)
    out(fig, "invoice_leaks", SOLUTION_FIGURES)        # names the planted leaks: kept with the solutions


# ---------------------------------------------------------------- 2. pure noise: selection and best-of-N
def fig_noise() -> None:
    demo = load(UNIT / "example" / "selection_leak_demo.py", "selection_leak_demo")
    ps = [20, 200, 2000]
    leaky, correct = [], []
    for p in ps:
        a, b = demo.selection_experiment(100, p)
        leaky.append(a)
        correct.append(b)
        print(f"selection_leak: n=100 p={p}: selection on all rows {a:.3f}, inside the pipeline {b:.3f}")
    best = demo.best_of_n_experiment()
    for n, v in best.items():
        print(f"best_of_n: N={n}: {v:.3f}")

    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.5), sharey=True)
    ax = axes[0]
    ax.plot(ps, leaky, color=LEAKY, marker="o", label="selection on all rows, then CV")
    ax.plot(ps, correct, color=HONEST, marker="s", label="selection inside the CV pipeline")
    ax.annotate("leaky", (ps[-1], leaky[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=9, color=INK["secondary"])
    ax.annotate("honest", (ps[-1], correct[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                fontsize=9, color=INK["secondary"])
    ax.set_xscale("log")
    ax.set_xticks(ps, [str(p) for p in ps])
    ax.set_xlabel("number of pure-noise features (100 rows, keep 20)")
    ax.set_ylabel("mean cross-validated ROC AUC")
    ax.set_title("Selecting on all rows invents skill")
    ax.axhline(0.5, color=INK["muted"], linewidth=1, linestyle=":")
    ax.legend(loc="upper left")
    ax = axes[1]
    ns = list(best)
    ax.plot(ns, [best[n] for n in ns], color=LEAKY, marker="o", label="best test AUC among N configurations")
    ax.axhline(0.5, color=INK["muted"], linewidth=1, linestyle=":")
    ax.text(ns[-1], 0.505, "true AUC 0.5", ha="right", va="bottom", fontsize=9, color=INK["secondary"])
    ax.set_xscale("log")
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_xlabel("configurations tried on the same test set")
    ax.set_title("Choosing the best on test inflates it")
    ax.legend(loc="upper left")
    fig.suptitle("Pure noise, true ROC AUC = 0.5 (SYNTHETIC, mean of 20 repetitions)", x=0.01, ha="left",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    out(fig, "noise_selection")


# ---------------------------------------------------------------- 3. SKAB: the clock
def fig_onsets() -> None:
    raw = ROOT / "data" / "raw" / "skab"
    files = sorted(raw.glob("*/*.csv"))
    if not files:
        print("skab_onsets: skipped (run `python project/get_skab.py` first)")
        return
    rows = []
    for f in files:
        df = pd.read_csv(f, sep=";")
        if "anomaly" not in df:
            continue
        flagged = df.index[df["anomaly"] == 1]
        rows.append({"experiment": f"{f.parent.name}/{f.stem}", "family": f.parent.name, "rows": len(df),
                     "onset": int(flagged.min()), "end": int(flagged.max())})
    onsets = pd.DataFrame(rows)
    order = {"valve1": 0, "valve2": 1, "other": 2}
    onsets = onsets.sort_values(["family", "onset"], key=lambda s: s.map(order) if s.name == "family" else s)
    print("skab_onsets:", onsets.groupby("family")["onset"].agg(["count", "min", "median", "max"]).to_dict())
    print("skab_onsets: onset in 550-600:", int(onsets["onset"].between(550, 600).sum()), "of", len(onsets))

    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    colours = {"valve1": SERIES[0], "valve2": SERIES[2], "other": SERIES[6]}
    for y, r in enumerate(onsets.itertuples()):
        ax.plot([0, r.rows - 1], [y, y], color=INK["grid"], linewidth=3, solid_capstyle="butt")
        ax.plot([r.onset, r.end], [y, y], color=colours[r.family], linewidth=3, solid_capstyle="butt")
    ax.axvspan(550, 600, color=INK["muted"], alpha=0.18, linewidth=0)
    ax.text(605, -1.0, "rows 550-600", ha="left", va="center", fontsize=9, color=INK["secondary"])
    ax.set_yticks(range(len(onsets)), onsets["experiment"], fontsize=7)
    ax.set_ylim(-1.8, len(onsets))
    ax.invert_yaxis()
    ax.set_xlabel("row within the experiment (about 1 row per second)")
    ax.set_title("SKAB: 31 of 34 anomalies start in rows 550-600 (real data)")
    handles = [plt.Line2D([], [], color=c, linewidth=3, label=f) for f, c in colours.items()]
    handles.append(plt.Line2D([], [], color=INK["grid"], linewidth=3, label="normal rows"))
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncols=4)
    ax.grid(axis="y", visible=False)
    out(fig, "skab_onsets")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", type=Path, default=None)
    ap.add_argument("--only", choices=["onsets", "invoices", "noise"], default=None)
    args = ap.parse_args()
    if args.png:
        args.png.mkdir(parents=True, exist_ok=True)
        PNG_DIR = args.png
    for name, fn in (("onsets", fig_onsets), ("invoices", fig_invoice_leaks), ("noise", fig_noise)):
        if args.only in (None, name):
            fn()
