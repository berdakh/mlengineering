"""Command-line entry point: ``pumpwatch train --config configs/base.toml``.

This module is the *application*: the only place that parses arguments,
configures logging and decides where output goes. stdout carries the result
(one JSON object); diagnostics go to stderr and to the run's log file.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from pumpwatch import __version__
from pumpwatch.compare import RunDirError, compare_runs
from pumpwatch.config import ConfigError, load_config
from pumpwatch.features import build_feature_table
from pumpwatch.io import load_windows
from pumpwatch.logging_setup import setup_logging
from pumpwatch.model import train_and_evaluate
from pumpwatch.runs import collect_environment, create_run_dir, write_json

logger = logging.getLogger("pumpwatch.cli")  # not __name__: under `python -m` that is "__main__"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pumpwatch", description="Pump fault detection.")
    parser.add_argument("--version", action="version", version=f"pumpwatch {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    train = sub.add_parser("train", help="train and evaluate; writes a run directory")
    train.add_argument("--config", required=True, help="path to a TOML config file")
    train.add_argument("--set", dest="overrides", action="append", default=[],
                       metavar="SECTION.KEY=VALUE", help="override one config value (repeatable)")
    train.add_argument("--run-dir", default="runs", help="parent directory for run folders")
    compare = sub.add_parser("compare-runs", help="diff the config and metrics of two run directories")
    compare.add_argument("run_a")
    compare.add_argument("run_b")
    return parser


def run_train(args: argparse.Namespace) -> int:
    try:
        cfg = load_config(args.config, args.overrides)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    resolved = cfg.to_dict()
    run_dir = create_run_dir(args.run_dir, resolved)
    setup_logging(cfg.logging.level, run_dir / "train.log")
    write_json(run_dir / "config.json", resolved)   # snapshot FIRST: it survives a crash
    logger.info("run started run_dir=%s seed=%d", run_dir, cfg.split.seed)

    try:
        df = load_windows(cfg.data.path)
        write_json(run_dir / "environment.json", collect_environment(cfg.data.path))
        features = build_feature_table(df, fs=cfg.data.fs)
        metrics = train_and_evaluate(features, cfg.split.test_fraction, cfg.split.seed, cfg.model.C)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("run failed error=%s", exc)
        return 2
    except Exception:
        logger.exception("run crashed")              # traceback goes to the log file too
        return 1

    write_json(run_dir / "metrics.json", metrics)
    logger.info("run finished auc=%.4f f1=%.4f", metrics["auc"], metrics["f1"])
    print(json.dumps({"run_dir": str(run_dir), "metrics": metrics}, indent=2))
    return 0


def run_compare(args: argparse.Namespace) -> int:
    try:
        report = compare_runs(args.run_a, args.run_b)
    except RunDirError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "compare-runs":
        return run_compare(args)
    return run_train(args)


if __name__ == "__main__":
    sys.exit(main())
