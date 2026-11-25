"""Command line (GIVEN in this lab): sweeps and the run registry.

    flowguard sweep --spec sweeps/mahalanobis.toml [--runs-dir runs]
    flowguard runs table [--runs-dir runs] [--metric NAME] [--sweep NAME]
    flowguard runs reproduce RUN_ID [--runs-dir runs]
    flowguard runs show RUN_ID [--runs-dir runs]

Exit codes: 0 success; 1 a run failed or a reproduction did not match; 2 usage or input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from flowguard import __version__
from flowguard import tracking


def _markdown(frame) -> str:
    cols = list(frame.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in frame.itertuples(index=False):
        cells = [(str(int(v)) if v.is_integer() and abs(v) >= 1 else f"{v:.4f}") if isinstance(v, float)
                 else str(v) for v in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def cmd_sweep(args) -> int:
    try:
        spec = tracking.load_spec(args.spec)
        configs = tracking.expand_sweep(spec)
    except (OSError, KeyError, ValueError) as exc:
        print(f"error: cannot expand {args.spec}: {exc}", file=sys.stderr)
        return 2
    counts = {"complete": 0, "skipped": 0, "failed": 0}
    for i, config in enumerate(configs, 1):
        result = tracking.execute(config, args.runs_dir)
        counts[result["status"]] += 1
        print(f"[{i}/{len(configs)}] {result['run_id']} {result['status']}", file=sys.stderr)
    tracking.write_index(args.runs_dir)
    print(json.dumps({"sweep": spec["sweep"]["name"], "runs": len(configs), **counts}))
    return 1 if counts["failed"] else 0


def cmd_table(args) -> int:
    index = tracking.write_index(args.runs_dir)
    if index.empty:
        print(f"error: no runs in {args.runs_dir}", file=sys.stderr)
        return 2
    if args.sweep:
        index = index[index["sweep"] == args.sweep]
    metric = args.metric or next((c[len("metric."):] for c in index.columns if c.startswith("metric.")), None)
    if metric is None:
        print("error: no complete run has metrics yet", file=sys.stderr)
        return 2
    try:
        table = tracking.aggregate(index, metric)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    table = table.loc[:, [c for c in table.columns if not (table[c].astype(str) == "-").all()]]
    constant = [c for c in table.columns if c.startswith("param.") and table[c].astype(str).nunique() == 1]
    if constant and len(table) > 1:
        print("same for every row: " + ", ".join(f"{c[len('param.'):]}={table[c].iloc[0]}" for c in constant))
        table = table.drop(columns=constant)
    print(f"metric: {metric}  (runs: {len(index)}; complete: {(index['status'] == 'complete').sum()}; "
          f"failed: {(index['status'] == 'failed').sum()}; partial: {(index['status'] == 'partial').sum()})")
    print(_markdown(table))
    return 0


def cmd_reproduce(args) -> int:
    try:
        result = tracking.reproduce(args.run_id, args.runs_dir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, default=str))
    return 0 if result["match"] else 1


def cmd_show(args) -> int:
    run_dir = Path(args.runs_dir) / args.run_id
    if not run_dir.is_dir():
        print(f"error: no run {args.run_id!r}", file=sys.stderr)
        return 2
    for name in ("config.json", "status.json", "metrics.json", "environment.json"):
        path = run_dir / name
        print(f"--- {name}")
        print(path.read_text() if path.is_file() else "(missing)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flowguard", description="flowguard sweeps and run registry")
    parser.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sweep = sub.add_parser("sweep", help="expand a sweep spec and execute every run")
    sweep.add_argument("--spec", required=True)
    sweep.add_argument("--runs-dir", default="runs")
    sweep.set_defaults(func=cmd_sweep)
    runs = sub.add_parser("runs", help="inspect the run registry").add_subparsers(dest="runs_command", required=True)
    table = runs.add_parser("table", help="aggregate complete runs over seeds")
    table.add_argument("--runs-dir", default="runs")
    table.add_argument("--metric")
    table.add_argument("--sweep")
    table.set_defaults(func=cmd_table)
    rep = runs.add_parser("reproduce", help="re-run a stored config and compare metrics")
    rep.add_argument("run_id")
    rep.add_argument("--runs-dir", default="runs")
    rep.set_defaults(func=cmd_reproduce)
    show = runs.add_parser("show", help="print a run directory")
    show.add_argument("run_id")
    show.add_argument("--runs-dir", default="runs")
    show.set_defaults(func=cmd_show)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
