"""The two verified leaks in the project data, measured on the REAL SKAB files.

    python project/get_skab.py                              # once, from the repo root
    python lessons/w3d1_leakage/example/skab_leaks.py

Uses only pandas so that it runs before you have written any lab code.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pandas as pd

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "project" / "get_skab.py").is_file())
RAW = ROOT / "data" / "raw" / "skab"


def load() -> dict[str, pd.DataFrame]:
    files = sorted(RAW.glob("*/*.csv"))
    if not files:
        sys.exit(f"no SKAB files under {RAW}. Run `python project/get_skab.py` first.")
    return {f"{f.parent.name}/{f.stem}": pd.read_csv(f, sep=";") for f in files}


def duplicate_pairs(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Every pair of files that shares rows identical in timestamp and all eight sensors."""
    key = [c for c in next(iter(frames.values())).columns if c not in ("anomaly", "changepoint")]
    rows = []
    for a, b in itertools.combinations(sorted(frames), 2):
        fa = frames[a].assign(**{c: frames[a].get(c, 0.0) for c in ("anomaly",)})
        fb = frames[b].assign(**{c: frames[b].get(c, 0.0) for c in ("anomaly",)})
        both = fa.merge(fb, on=key, suffixes=("_a", "_b"))
        if len(both):
            rows.append({"file_a": a, "file_b": b, "shared_rows": len(both),
                         "contradictory_labels": int((both["anomaly_a"] != both["anomaly_b"]).sum()),
                         "share_of_b": round(len(both) / len(fb), 3)})
    return pd.DataFrame(rows)


def onset_table(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, df in frames.items():
        if "anomaly" not in df:
            continue
        flagged = df.index[df["anomaly"] == 1]
        rows.append({"experiment": name, "family": name.split("/")[0], "rows": len(df),
                     "onset_row": int(flagged.min()), "last_anomalous_row": int(flagged.max())})
    return pd.DataFrame(rows)


def main() -> None:
    frames = load()
    pairs = duplicate_pairs(frames)
    print("files sharing identical rows (timestamp + 8 sensors):")
    print(pairs.to_string(index=False))
    print(f"total shared rows {pairs['shared_rows'].sum()}, with contradictory labels {pairs['contradictory_labels'].sum()}")

    onsets = onset_table(frames)
    print("\nanomaly onset row by family (min / median / max):")
    print(onsets.groupby("family")["onset_row"].agg(["count", "min", "median", "max"]).to_string())
    in_band = int(onsets["onset_row"].between(550, 600).sum())
    print(f"experiments with onset in rows 550-600: {in_band} of {len(onsets)}")
    rule = pd.concat([(df.index.to_series() >= 570).astype(int).rename("pred").to_frame().assign(y=df["anomaly"])
                      for df in frames.values() if "anomaly" in df])
    tp = int(((rule.pred == 1) & (rule.y == 1)).sum())
    precision, recall = tp / int(rule.pred.sum()), tp / int(rule.y.sum())
    print(f"rule 'row >= 570 is anomalous', no sensors: precision {precision:.3f}, recall {recall:.3f}, "
          f"F1 {2 * precision * recall / (precision + recall):.3f}")


if __name__ == "__main__":
    main()
