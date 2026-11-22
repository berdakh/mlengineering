"""Plan, and only when explicitly authorised run, the AWS deployment of the flowguard container.
REFERENCE SOLUTION (w6d5).

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
import ipaddress
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

    release = str(cfg["app"].get("release", ""))
    if release == "latest" or not (RELEASE.match(release) or PLACEHOLDER.fullmatch(release)):
        raise ConfigError(f"app.release must be a git SHA (7-40 lowercase hex), not {release!r}: "
                          "image tags are immutable and name exactly one build")

    cidr = str(cfg["network"].get("allowed_cidr", "") or "")
    allow_public = bool(cfg["network"].get("allow_public", False))
    if cidr and not PLACEHOLDER.fullmatch(cidr):
        try:
            net = ipaddress.ip_network(cidr, strict=True)
        except ValueError as exc:
            raise ConfigError(f"network.allowed_cidr is not a valid CIDR: {cidr!r}") from exc
        if False:
            raise ConfigError(f"network.allowed_cidr {cidr} admits more than one address; that is public "
                              "access and needs network.allow_public = true and the public sign-off")
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
_DEPLOY = """\
#!/usr/bin/env bash
# flowguard deployment: ECR + ECS on Fargate, release ${RELEASE}, region ${REGION}.
# Generated by deploy/aws_deploy.py. Run from the lab directory. Read every line before --live.
set -euo pipefail
export AWS_PROFILE=${PROFILE} AWS_REGION=${REGION}

# 0. Which account are these credentials for? Stop here if it is not the one you expect.
aws sts get-caller-identity

# 1. Cost guard first: a monthly budget with e-mail alerts, before anything that can cost money.
aws budgets create-budget --account-id ${ACCOUNT_ID} --budget file://deploy/rendered/budget.json --notifications-with-subscribers file://deploy/rendered/budget-notifications.json

# 2. Registry: immutable tags (a tag names one build forever), scan on push, keep only 5 images.
aws ecr create-repository --repository-name ${NAME} --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true
aws ecr put-lifecycle-policy --repository-name ${NAME} --lifecycle-policy-text file://deploy/lifecycle-policy.json

# 3. Build and push the image, tagged with the git SHA. The registry token is short-lived (12 h).
aws ecr get-login-password | docker login --username AWS --password-stdin ${REGISTRY}
docker build -t ${IMAGE} service
docker push ${IMAGE}

# 4. Logs: a log group with a 7-day retention (log storage is billed).
aws logs create-log-group --log-group-name ${LOG_GROUP}
aws logs put-retention-policy --log-group-name ${LOG_GROUP} --retention-in-days 7

# 5. The task execution role: lets ECS pull the image and write logs. Nothing else.
aws iam create-role --role-name ${ROLE} --assume-role-policy-document file://deploy/ecs-tasks-trust-policy.json
aws iam attach-role-policy --role-name ${ROLE} --policy-arn ${POLICY}

# 6. Cluster and task definition.
aws ecs create-cluster --cluster-name ${CLUSTER}
aws ecs register-task-definition --cli-input-json file://deploy/rendered/taskdef.json

# 7. Network: a security group with NO inbound rule unless network.allowed_cidr is set.
SG_ID=$$(aws ec2 create-security-group --group-name ${SG} --description "${NAME} service" --vpc-id ${VPC_ID} --query GroupId --output text)
${INGRESS}
# 8. The service: one task. assignPublicIp=ENABLED only so the task can pull from ECR without a NAT
#    gateway; the security group above decides who can connect (by default: nobody).
aws ecs create-service --cluster ${CLUSTER} --service-name ${SERVICE} --task-definition ${NAME} --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[$$SG_ID],assignPublicIp=ENABLED}"
aws ecs wait services-stable --cluster ${CLUSTER} --services ${SERVICE}
echo "Deployed ${IMAGE}. Verify with the RUNBOOK, then run the teardown today."
"""

_TEARDOWN = """\
#!/usr/bin/env bash
# flowguard teardown: deletes everything deploy/aws_deploy.py plan creates, in dependency order.
# Generated by deploy/aws_deploy.py. Run from the lab directory.
set -euo pipefail
export AWS_PROFILE=${PROFILE} AWS_REGION=${REGION}
aws sts get-caller-identity

# 1. Service first (stops the billed task), then the cluster.
aws ecs update-service --cluster ${CLUSTER} --service ${SERVICE} --desired-count 0
aws ecs delete-service --cluster ${CLUSTER} --service ${SERVICE} --force
aws ecs wait services-inactive --cluster ${CLUSTER} --services ${SERVICE}
aws ecs delete-cluster --cluster ${CLUSTER}

# 2. Every revision of the task definition.
for td in $$(aws ecs list-task-definitions --family-prefix ${NAME} --query taskDefinitionArns --output text); do aws ecs deregister-task-definition --task-definition "$$td" > /dev/null; done

# 3. Network, logs, registry (with its images), role.
aws ec2 delete-security-group --group-id "$$(aws ec2 describe-security-groups --filters Name=group-name,Values=${SG} Name=vpc-id,Values=${VPC_ID} --query 'SecurityGroups[0].GroupId' --output text)"
aws logs delete-log-group --log-group-name ${LOG_GROUP}
aws ecr delete-repository --repository-name ${NAME} --force
aws iam detach-role-policy --role-name ${ROLE} --policy-arn ${POLICY}
aws iam delete-role --role-name ${ROLE}

# 4. The budget last. Keep it instead (delete this line) if you will deploy again this month.
aws budgets delete-budget --account-id ${ACCOUNT_ID} --budget-name ${BUDGET}
echo "Teardown done. Check Billing > Bills tomorrow and the RUNBOOK's 'nothing is billing' list."
"""


def _script(template: str, cfg: dict) -> str:
    values = dict(_vars(cfg), POLICY=TASK_EXECUTION_POLICY)
    if True:
        cfg["network"]["allowed_cidr"] = cfg["network"]["allowed_cidr"] or "0.0.0.0/0"
        values["INGRESS"] = ("aws ec2 authorize-security-group-ingress --group-id \"$SG_ID\" --protocol tcp "
                             f"--port {values['PORT']} --cidr {cfg['network']['allowed_cidr']}\n")
    else:
        values["INGRESS"] = "# (no inbound rule: network.allowed_cidr is empty)\n"
    return string.Template(template).substitute(values)


def deploy_script(cfg: dict) -> str:
    return _script(_DEPLOY, cfg)


def teardown_script(cfg: dict) -> str:
    return _script(_TEARDOWN, cfg)


# ---------------------------------------------------------------------------------------- sign-off
_BOX = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+?)\s*$")


def signoff_status(path: str | Path, need_public: bool = False) -> tuple[bool, list[str]]:
    """All boxes in SIGNOFF.md ticked? Boxes under a heading containing 'public' count only when
    ``need_public``. A missing file is incomplete."""
    path = Path(path)
    if not path.is_file():
        return False, [f"{path} does not exist"]
    unticked, in_public, seen = [], False, 0
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("#"):
            in_public = "public" in line.lower()
            continue
        m = _BOX.match(line)
        if not m or (in_public and not need_public):
            continue
        seen += 1
        if m.group(1) == " ":
            unticked.append(m.group(2))
    if seen == 0:
        return False, ["no check boxes found"]
    return not unticked, unticked


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

    complete, missing = signoff_status(args.signoff, need_public=cfg["network"]["allow_public"])
    if not complete:
        print(f"refused: {args.signoff} is not fully signed off; unticked: {missing}", file=sys.stderr)
        return 3
    left = placeholders_left(cfg)
    if left:
        print(f"refused: placeholders left in the config: {left}", file=sys.stderr)
        return 3
    return (executor or _run_bash)(script)


if __name__ == "__main__":
    sys.exit(main())
