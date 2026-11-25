"""Command line: monitor-demo, registry.

    python -m flowguard monitor-demo --raw data/raw/skab --splits splits/v2.json \
        --scenario scenarios/demo.toml --out reports
    python -m flowguard registry show --root reports/registry
    python -m flowguard registry rollback --root reports/registry --reason "alarm rate above budget"
"""
from __future__ import annotations

import argparse
import sys

from flowguard import __version__


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="flowguard", description=__doc__.split("\n")[0])
    p.add_argument("--version", action="version", version=f"flowguard {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("monitor-demo", help="run the scripted monitoring scenario and write the report")
    d.add_argument("--raw", required=True)
    d.add_argument("--splits", required=True)
    d.add_argument("--scenario", required=True)
    d.add_argument("--out", required=True)
    d.add_argument("--config", default="configs/model.toml")
    d.add_argument("--settings", default="configs/service.toml")
    r = sub.add_parser("registry", help="inspect or change the registry's CURRENT pointer")
    r.add_argument("action", choices=["show", "promote", "rollback"])
    r.add_argument("--root", required=True)
    r.add_argument("--version", help="for promote")
    r.add_argument("--reason", default="")
    return p


def registry_command(args: argparse.Namespace) -> int:
    from flowguard.registry import Registry, RegistryError
    reg = Registry(args.root)
    try:
        if args.action == "promote":
            if not args.version:
                print("error: promote needs --version", file=sys.stderr)
                return 2
            reg.promote(args.version, args.reason)
        elif args.action == "rollback":
            reg.rollback(args.reason)
    except RegistryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"current: {reg.current()}  (versions: {', '.join(reg.versions())})")
    for h in reg.history()[-5:]:
        print(f"  {h['action']:8s} {h['version']}  {h['reason']}")
    if args.action != "show":
        print("Restart the service and check /version: the running process still serves the old version.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "registry":
        return registry_command(args)
    from flowguard.demo import run_demo
    results = run_demo(args.raw, args.splits, args.scenario, args.out, args.config, args.settings)
    s = results["summary"]
    print(f"{s['events_as_expected']}/{s['events']} events as expected; report: {args.out}/monitoring_demo.md")
    return 0 if results["server"]["stopped"] else 1
