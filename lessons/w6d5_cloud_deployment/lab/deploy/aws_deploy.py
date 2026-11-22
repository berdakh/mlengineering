"""Plan, and only when explicitly authorised run, the AWS deployment of the flowguard container.
YOU COMPLETE THIS MODULE (w6d5, tasks 3-6).

    python deploy/aws_deploy.py plan     --config deploy/config.toml          # dry run (default)
    python deploy/aws_deploy.py teardown --config deploy/config.toml          # dry run
    python deploy/aws_deploy.py plan     --config deploy/config.toml --live   # runs it, if signed off

Run from the lab directory (the one that contains ``service/`` and ``deploy/``).

Design
------
* The output of a dry run IS the deployment: a bash script, one AWS CLI or Docker command per line,
  every placeholder substituted from the config. ``--live`` hands exactly that text to bash, so what
  you reviewed is what runs. Nothing is executed without ``--live``.
* ``--live`` refuses to start unless (1) every box in ``deploy/SIGNOFF.md`` is ticked (the public-
  access boxes only when ``allow_public = true``) and (2) no ``<placeholder>`` is left in the config.
* Route: Amazon ECR + Amazon ECS on AWS Fargate, one task, no load balancer. Default network
  exposure: none (``allowed_cidr = ""`` adds no inbound rule). See the lesson for why.
* No credentials are read, stored or printed here. The AWS CLI gets short-lived credentials from
  the SSO profile named in the config.

Contract (graded by the checks)
-------------------------------
``load_config(path, env) -> dict``          TOML + environment overrides, validated; ``ConfigError``
``render_task_definition(cfg) -> dict``     the ECS task definition as a dict
``deploy_script(cfg) -> str``               the deployment script (bash)
``teardown_script(cfg) -> str``             the teardown script (bash)
``signoff_status(path, need_public) -> (bool, list[str])``   complete?, unticked items
``main(argv, executor=None, env=None) -> int``  exit codes: 0 ok, 2 config error, 3 refused
"""
from __future__ import annotations

import argparse
import ipaddress  # noqa: F401  (you will need it)
import json
import os
import re
import string
import subprocess
import sys
import tomllib
from collections.abc import Callable, Mapping
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
TASK_EXECUTION_POLICY = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
ENV_OVERRIDES = {  # environment variable -> (section, key)
    "FLOWGUARD_AWS_ACCOUNT_ID": ("aws", "account_id"),
    "FLOWGUARD_RELEASE": ("app", "release"),
    "FLOWGUARD_ALLOWED_CIDR": ("network", "allowed_cidr"),
}
PLACEHOLDER = re.compile(r"<[^<>]+>")
RELEASE = re.compile(r"^[0-9a-f]{7,40}$")


class ConfigError(ValueError):
    """The configuration is invalid; the message names the key."""


# ----------------------------------------------------------------------------------- configuration
def load_config(path: str | Path, env: Mapping[str, str] | None = None) -> dict:
    env = os.environ if env is None else env
    with open(path, "rb") as fh:
        cfg = tomllib.load(fh)
    for section in ("aws", "app", "network", "budget"):
        cfg.setdefault(section, {})
    for var, (section, key) in ENV_OVERRIDES.items():
        if env.get(var):
            cfg[section][key] = env[var]

    # TODO (task 3): validate, raising ConfigError with a message that names the key:
    #   * app.release must be a git SHA (7-40 lowercase hex) or still a <placeholder>; never "latest";
    #   * network.allowed_cidr: "" (no inbound rule) or a valid CIDR (or a <placeholder>); a CIDR that
    #     admits more than one address is public and needs network.allow_public = true.
    cidr = str(cfg["network"].get("allowed_cidr", "") or "")
    allow_public = bool(cfg["network"].get("allow_public", False))
    cfg["network"]["allowed_cidr"] = cidr
    cfg["network"]["allow_public"] = allow_public
    return cfg


def placeholders_left(cfg: dict) -> list[str]:
    """Dotted keys whose value still contains a <placeholder>."""
    return [f"{section}.{key}" for section, values in cfg.items() for key, value in values.items()
            if isinstance(value, str) and PLACEHOLDER.search(value)]


def _vars(cfg: dict) -> dict[str, str]:
    a, app, net = cfg["aws"], cfg["app"], cfg["network"]
    name, region, account = app["name"], a["region"], str(a["account_id"])
    registry = f"{account}.dkr.ecr.{region}.amazonaws.com"
    return {
        "NAME": name, "REGION": region, "ACCOUNT_ID": account, "PROFILE": a["profile"],
        "RELEASE": app["release"], "PORT": str(app.get("container_port", 8000)),
        "CPU": str(app.get("cpu", "256")), "MEMORY": str(app.get("memory", "512")),
        "REGISTRY": registry, "IMAGE": f"{registry}/{name}:{app['release']}",
        "CLUSTER": f"{name}-cluster", "SERVICE": f"{name}-svc", "LOG_GROUP": f"/ecs/{name}",
        "ROLE": f"{name}-task-execution", "SG": f"{name}-sg", "BUDGET": f"{name}-budget",
        "VPC_ID": net["vpc_id"], "SUBNET_ID": net["subnet_id"], "CIDR": net["allowed_cidr"],
        "LIMIT_USD": str(cfg["budget"].get("limit_usd", 10)),
        "NOTIFY_EMAIL": cfg["budget"].get("notify_email", ""),
    }


def _render(template_name: str, cfg: dict) -> str:
    return string.Template((HERE / template_name).read_text()).substitute(_vars(cfg))


def render_task_definition(cfg: dict) -> dict:
    return json.loads(_render("taskdef.template.json", cfg))


def write_rendered(cfg: dict, out_dir: Path) -> None:
    """Write the JSON files the scripts reference (taskdef, budget) into ``out_dir``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "taskdef.json").write_text(json.dumps(render_task_definition(cfg), indent=2) + "\n")
    (out_dir / "budget.json").write_text(_render("budget.template.json", cfg))
    (out_dir / "budget-notifications.json").write_text(_render("budget-notifications.template.json", cfg))


# ----------------------------------------------------------------------------------------- scripts
def deploy_script(cfg: dict) -> str:
    """TODO (task 4): return the deployment as a bash script (see the lesson, section 4, for the
    required steps and their order). Requirements the checks test:

    * starts with ``set -euo pipefail`` and ``export AWS_PROFILE=... AWS_REGION=...``;
    * ``aws sts get-caller-identity`` first; ``aws budgets create-budget`` before anything billable;
    * ECR repository with ``--image-tag-mutability IMMUTABLE`` and scan on push, a lifecycle policy;
    * ``docker build``/``docker push`` of ``<registry>/<name>:<release>`` (never ``latest``);
    * a log group with a retention policy; the task execution role with the managed policy
      ``TASK_EXECUTION_POLICY`` attached; a cluster; ``register-task-definition`` from
      ``deploy/rendered/taskdef.json``; a security group, with an inbound rule ONLY when
      ``network.allowed_cidr`` is non-empty (and then exactly that CIDR on the container port);
    * ``aws ecs create-service`` with ``--launch-type FARGATE`` after the task definition is registered.

    ``_vars(cfg)`` gives every name you need. Every placeholder must be substituted.
    """
    raise NotImplementedError


def teardown_script(cfg: dict) -> str:
    """TODO (task 5): the teardown as a bash script: deletes every resource type the deploy script
    creates, in dependency order (service before cluster, detach the policy before deleting the role,
    the service before the security group)."""
    raise NotImplementedError


# ---------------------------------------------------------------------------------------- sign-off
_BOX = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+?)\s*$")


def signoff_status(path: str | Path, need_public: bool = False) -> tuple[bool, list[str]]:
    """TODO (task 6): are all boxes in SIGNOFF.md ticked? Returns ``(complete, unticked_items)``.

    A box is a Markdown list item ``- [ ] text`` (unticked) or ``- [x] text`` (ticked). Boxes under a
    heading whose text contains "public" count only when ``need_public``. A missing file, or a file
    with no boxes at all, is incomplete.
    """
    raise NotImplementedError


# -------------------------------------------------------------------------------------------- main
def _run_bash(script: str) -> int:
    return subprocess.run(["bash", "-c", script], cwd=LAB, check=False).returncode


def main(argv: list[str] | None = None, executor: Callable[[str], int] | None = None,
         env: Mapping[str, str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Plan or (with --live) run the AWS deployment.")
    ap.add_argument("action", choices=["plan", "teardown"])
    ap.add_argument("--config", default=str(HERE / "config.toml"))
    ap.add_argument("--signoff", default=str(HERE / "SIGNOFF.md"))
    ap.add_argument("--out-dir", default=str(HERE / "rendered"), help="where rendered JSON files go")
    ap.add_argument("--live", action="store_true", help="execute the script (needs the sign-off)")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config, env)
    except (ConfigError, OSError, tomllib.TOMLDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    script = deploy_script(cfg) if args.action == "plan" else teardown_script(cfg)
    if args.action == "plan":
        write_rendered(cfg, Path(args.out_dir))   # local JSON files the script reads; inspect them

    if not args.live:
        print(script, end="")
        print("# DRY RUN: nothing was executed. Review, then see deploy/RUNBOOK.md.", file=sys.stderr)
        return 0

    # TODO (task 6): refuse (message on stderr, return 3) unless signoff_status(...) is complete
    # (public boxes required when network.allow_public) AND placeholders_left(cfg) is empty.
    return (executor or _run_bash)(script)


if __name__ == "__main__":
    sys.exit(main())
