"""Command line: build-model, predict-batch, evaluate.

    python -m flowguard build-model --config configs/model.toml --splits splits/v2.json --raw data/raw/skab --out models/current
    python -m flowguard predict-batch --model models/current --raw data/raw/skab --split test --out predictions/test.csv
    python -m flowguard evaluate --model models/current --raw data/raw/skab --splits splits/v2.json --split test
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path

import pandas as pd

from flowguard import __version__
from flowguard.bundle import BundleError, load_bundle, save_bundle
from flowguard.data import load_raw
from flowguard.evaluation import experiment_scores, point_summary
from flowguard.inference import score_experiments
from flowguard.scoring import ZScoreModel
from flowguard.splits import dev_experiments, file_sha256, load_splits

MODEL_KEYS = {"model_version", "sensor", "n_burn_in", "threshold", "min_duration", "merge_gap"}


def _select(tidy: pd.DataFrame, splits_path: str | None, split: str) -> pd.DataFrame:
    if split == "all":
        return tidy
    if splits_path is None:
        raise SystemExit("error: --split test/dev needs --splits")
    manifest = load_splits(splits_path)
    ids = manifest["test"] if split == "test" else dev_experiments(manifest)
    missing = sorted(set(ids) - set(tidy["experiment_id"]))
    if missing:
        raise SystemExit(f"error: experiments in the manifest but not in the data: {missing[:5]}")
    return tidy[tidy["experiment_id"].isin(set(ids))]


def build_model(args: argparse.Namespace) -> int:
    """TODO (milestone 2): package configs/model.toml as a bundle in args.out.

    Validate the config keys (MODEL_KEYS), check the split manifest with load_splits, and record
    provenance in the bundle: the config, sha256 of the config file, sha256 of the split manifest, and
    something that identifies the development data the operating point was chosen on.
    """
    raise NotImplementedError("build-model")


def predict_batch(args: argparse.Namespace) -> int:
    """TODO (milestone 2): score the selected experiments with the packaged inference and write a CSV
    with columns experiment_id, t, score, above_threshold. A missing or broken bundle must end with a
    one-line error and a non-zero exit code, not a traceback.
    """
    raise NotImplementedError("predict-batch")


def evaluate(args: argparse.Namespace) -> int:
    model = load_bundle(args.model)
    tidy = _select(load_raw(args.raw), args.splits, args.split)
    summary = point_summary(experiment_scores(model, tidy), model.n_burn_in)
    print(json.dumps({"model_version": model.model_version, "split": args.split, **summary}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="flowguard", description=__doc__.split("\n")[0])
    p.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build-model", help="package the configured detector as a bundle")
    b.add_argument("--config", required=True)
    b.add_argument("--splits", required=True)
    b.add_argument("--raw", required=True)
    b.add_argument("--out", required=True)
    b.set_defaults(fn=build_model)
    for name, fn, help_ in (("predict-batch", predict_batch, "score experiments to a CSV"),
                            ("evaluate", evaluate, "point-level summary on a split")):
        s = sub.add_parser(name, help=help_)
        s.add_argument("--model", required=True)
        s.add_argument("--raw", required=True)
        s.add_argument("--splits")
        s.add_argument("--split", choices=["test", "dev", "all"], default="all")
        if name == "predict-batch":
            s.add_argument("--out", required=True)
        s.set_defaults(fn=fn)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)
