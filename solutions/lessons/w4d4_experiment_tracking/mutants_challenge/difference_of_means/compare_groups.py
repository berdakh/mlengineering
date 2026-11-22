"""Paired comparison of two groups of runs from the registry index (reference solution).

    python lessons/w4d4_experiment_tracking/challenge/compare_groups.py --runs-dir runs \
        --a detector.n_estimators=200 --b detector.n_estimators=50 --metric dev_pooled_pr_auc

Group A and group B are selected from the index with parameter filters. Runs are paired on the
seed (or another column): the pair (A, seed s) - (B, seed s) shares everything the seed controls,
so the difference cancels that shared variation. Only complete runs are used.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd


def _select(index: pd.DataFrame, filters: Mapping[str, Any]) -> pd.DataFrame:
    rows = index[index["status"] == "complete"]
    for key, value in filters.items():
        column = key if key in rows.columns else f"param.{key}"
        if column not in rows.columns:
            raise ValueError(f"unknown parameter {key!r}")
        rows = rows[rows[column] == value]
    return rows


def compare_groups(index: pd.DataFrame, a: Mapping[str, Any], b: Mapping[str, Any], metric: str,
                   pair_on: str = "seed") -> dict:
    """Mean and sd of paired differences A - B over the ``pair_on`` values present in both groups.

    Returns ``{"metric", "n_pairs", "pairs": [{pair_on, "a", "b", "diff"}], "mean_diff", "sd_diff",
    "a_better", "unmatched_a", "unmatched_b"}``. ``sd_diff`` uses ddof = 1 (NaN for one pair).
    Raises ValueError if there is no pair, or if a filter leaves several runs with the same
    ``pair_on`` value (the filter does not identify ONE configuration).
    """
    column = f"metric.{metric}"
    ga, gb = _select(index, a), _select(index, b)
    for name, group in (("A", ga), ("B", gb)):
        if group[pair_on].duplicated().any():
            raise ValueError(f"group {name} has several runs per {pair_on}: make its filter more specific")
    va = dict(zip(ga[pair_on], ga[column]))
    vb = dict(zip(gb[pair_on], gb[column]))
    shared = sorted(set(va) & set(vb))
    if not shared:
        raise ValueError(f"no {pair_on} value is present in both groups")
    pairs = [{pair_on: k, "a": float(va[k]), "b": float(vb[k]), "diff": float(va[k] - vb[k])} for k in shared]
    diffs = np.array([p["diff"] for p in pairs])
    return {"metric": metric, "n_pairs": len(pairs), "pairs": pairs,
            "mean_diff": float(np.mean(list(va.values())) - np.mean(list(vb.values()))),
            "sd_diff": float(diffs.std(ddof=1)) if len(diffs) > 1 else float("nan"),
            "a_better": int((diffs > 0).sum()),
            "unmatched_a": sorted(set(va) - set(vb)), "unmatched_b": sorted(set(vb) - set(va))}


def format_report(result: dict, a: Mapping[str, Any], b: Mapping[str, Any]) -> str:
    lines = [f"A = {dict(a)}  vs  B = {dict(b)}  on {result['metric']}",
             "| pair | A | B | A - B |", "|---|---|---|---|"]
    for p in result["pairs"]:
        key = next(k for k in p if k not in ("a", "b", "diff"))
        lines.append(f"| {p[key]} | {p['a']:.4f} | {p['b']:.4f} | {p['diff']:+.4f} |")
    lines.append(f"mean difference {result['mean_diff']:+.4f} (sd {result['sd_diff']:.4f}, "
                 f"{result['n_pairs']} pairs; A better in {result['a_better']})")
    if result["unmatched_a"] or result["unmatched_b"]:
        lines.append(f"unpaired and left out: A {result['unmatched_a']}, B {result['unmatched_b']}")
    return "\n".join(lines)


def _parse_filter(items: list[str]) -> dict:
    out = {}
    for item in items:
        key, _, raw = item.partition("=")
        try:
            out[key] = json.loads(raw)
        except json.JSONDecodeError:
            out[key] = raw
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", default="runs")
    ap.add_argument("--a", nargs="+", required=True, help="key=value filters for group A")
    ap.add_argument("--b", nargs="+", required=True, help="key=value filters for group B")
    ap.add_argument("--metric", required=True)
    ap.add_argument("--pair-on", default="seed")
    args = ap.parse_args(argv)
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here.parent / "lab" / "src"))
    from flowguard.tracking import build_index
    a, b = _parse_filter(args.a), _parse_filter(args.b)
    try:
        result = compare_groups(build_index(args.runs_dir), a, b, args.metric, args.pair_on)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(format_report(result, a, b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
