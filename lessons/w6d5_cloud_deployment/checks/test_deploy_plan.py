"""Checks for lesson w6d5: the deployment plan, the live gate, the teardown and the task definition.
No AWS call is made: the live path runs a fake executor."""
from __future__ import annotations

import json
import re

import pytest

from conftest import ACCOUNT, RELEASE, commands, first_index

REGISTRY = f"{ACCOUNT}.dkr.ecr.eu-central-1.amazonaws.com"


def plan(dep, cfg_path, capsys, tmp_path, *extra, env=None):
    code = dep.main(["plan", "--config", str(cfg_path), "--out-dir", str(tmp_path / "rendered"), *extra],
                    executor=lambda s: pytest.fail("dry run must not execute anything"), env=env or {})
    out = capsys.readouterr()
    return code, out.out, out.err


# ----------------------------------------------------------------------------------------- dry run
def test_dry_run_prints_a_complete_script_and_executes_nothing(dep, write_config, capsys, tmp_path):
    code, out, _ = plan(dep, write_config(), capsys, tmp_path)
    assert code == 0
    cmds = commands(out)
    assert cmds and cmds[0].startswith("set -euo pipefail"), "the script must start with `set -euo pipefail`"
    assert any(c.startswith("export AWS_PROFILE=flowguard-sso") and "AWS_REGION=eu-central-1" in c for c in cmds)
    leftover = [c for c in cmds if re.search(r"<[^<>]+>|\$\{[A-Z_]+\}", c)]
    assert not leftover, f"unsubstituted placeholders: {leftover}"


def test_order_identity_then_budget_then_billable_resources(dep, write_config, capsys, tmp_path):
    cmds = commands(plan(dep, write_config(), capsys, tmp_path)[1])
    i_id = first_index(cmds, "aws sts get-caller-identity")
    i_budget = first_index(cmds, "aws budgets create-budget")
    billable = [first_index(cmds, n) for n in ("aws ecr create-repository", "docker push",
                                               "aws logs create-log-group", "aws ecs create-service")]
    assert i_id < i_budget < min(billable), "identity check, then the budget, then anything billable"
    assert f"--account-id {ACCOUNT}" in cmds[i_budget]


def test_registry_is_immutable_scanned_and_image_tag_is_the_release(dep, write_config, capsys, tmp_path):
    cmds = commands(plan(dep, write_config(), capsys, tmp_path)[1])
    repo = cmds[first_index(cmds, "aws ecr create-repository")]
    assert "--image-tag-mutability IMMUTABLE" in repo and "scanOnPush=true" in repo
    first_index(cmds, "aws ecr put-lifecycle-policy")
    login = cmds[first_index(cmds, "docker login")]
    assert "get-login-password" in login and "--password-stdin" in login and REGISTRY in login
    image = f"{REGISTRY}/flowguard:{RELEASE}"
    assert image in cmds[first_index(cmds, "docker build")]
    assert image in cmds[first_index(cmds, "docker push")]
    assert not any(":latest" in c for c in cmds), "never deploy a mutable `latest` tag"


def test_role_cluster_taskdef_service_in_dependency_order(dep, write_config, capsys, tmp_path):
    cmds = commands(plan(dep, write_config(), capsys, tmp_path)[1])
    i_role = first_index(cmds, "aws iam create-role")
    i_attach = first_index(cmds, "aws iam attach-role-policy")
    assert "AmazonECSTaskExecutionRolePolicy" in cmds[i_attach]
    i_logs = first_index(cmds, "aws logs create-log-group")
    assert "--retention-in-days" in cmds[first_index(cmds, "aws logs put-retention-policy")]
    i_cluster = first_index(cmds, "aws ecs create-cluster")
    i_td = first_index(cmds, "aws ecs register-task-definition")
    assert "rendered/taskdef.json" in cmds[i_td]
    i_sg = first_index(cmds, "aws ec2 create-security-group")
    i_svc = first_index(cmds, "aws ecs create-service")
    assert max(i_role, i_attach, i_logs, i_cluster, i_td, i_sg) < i_svc
    assert "--launch-type FARGATE" in cmds[i_svc]


def test_no_inbound_rule_by_default(dep, write_config, capsys, tmp_path):
    cmds = commands(plan(dep, write_config(cidr=""), capsys, tmp_path)[1])
    assert not any("authorize-security-group-ingress" in c for c in cmds), \
        "with allowed_cidr empty the security group must have no inbound rule"


def test_single_address_ingress_on_the_container_port(dep, write_config, capsys, tmp_path):
    cmds = commands(plan(dep, write_config(cidr="203.0.113.7/32"), capsys, tmp_path)[1])
    rule = cmds[first_index(cmds, "authorize-security-group-ingress")]
    assert "--cidr 203.0.113.7/32" in rule and "--port 8000" in rule
    assert "0.0.0.0/0" not in "\n".join(cmds)


@pytest.mark.parametrize("cidr", ["0.0.0.0/0", "203.0.113.0/24"])
def test_wide_cidr_without_allow_public_is_a_config_error(dep, write_config, capsys, tmp_path, cidr):
    code, out, err = plan(dep, write_config(cidr=cidr), capsys, tmp_path)
    assert code == 2 and "allowed_cidr" in err and "0.0.0.0/0" not in out


def test_wide_cidr_with_allow_public_is_planned(dep, write_config, capsys, tmp_path):
    code, out, _ = plan(dep, write_config(cidr="203.0.113.0/24", public="true"), capsys, tmp_path)
    assert code == 0 and "--cidr 203.0.113.0/24" in out


@pytest.mark.parametrize("release", ["latest", "v1.2", "ABCDEF1"])
def test_release_must_be_a_git_sha(dep, write_config, capsys, tmp_path, release):
    code, _, err = plan(dep, write_config(release=release), capsys, tmp_path)
    assert code == 2 and "release" in err


def test_environment_overrides_the_config(dep, write_config, capsys, tmp_path):
    env = {"FLOWGUARD_AWS_ACCOUNT_ID": "999988887777", "FLOWGUARD_RELEASE": "feedface01"}
    code, out, _ = plan(dep, write_config(), capsys, tmp_path, env=env)
    assert code == 0 and "999988887777.dkr.ecr" in out and ":feedface01" in out


# ----------------------------------------------------------------------------------------- live gate
def live(dep, cfg_path, signoff_path, tmp_path, capsys, action="plan", env=None):
    ran = []
    code = dep.main([action, "--config", str(cfg_path), "--signoff", str(signoff_path),
                     "--out-dir", str(tmp_path / "rendered"), "--live"],
                    executor=lambda script: ran.append(script) or 0, env=env or {})
    return code, ran, capsys.readouterr()


def test_live_refused_without_signoff_file(dep, write_config, tmp_path, capsys):
    code, ran, out = live(dep, write_config(), tmp_path / "missing.md", tmp_path, capsys)
    assert code == 3 and not ran and "SIGN" in out.err.upper()


def test_live_refused_with_an_unticked_box(dep, write_config, signoff, tmp_path, capsys):
    code, ran, _ = live(dep, write_config(), signoff(required=False), tmp_path, capsys)
    assert code == 3 and not ran


def test_live_refused_while_placeholders_remain(dep, write_config, signoff, tmp_path, capsys):
    code, ran, out = live(dep, write_config(account="<ACCOUNT_ID>"), signoff(), tmp_path, capsys)
    assert code == 3 and not ran and "account_id" in out.err


def test_public_needs_the_public_boxes(dep, write_config, signoff, tmp_path, capsys):
    cfg = write_config(cidr="203.0.113.0/24", public="true")
    code, ran, _ = live(dep, cfg, signoff(public=False), tmp_path, capsys)
    assert code == 3 and not ran
    code, ran, _ = live(dep, cfg, signoff(public=True), tmp_path, capsys)
    assert code == 0 and len(ran) == 1


def test_signed_live_runs_exactly_the_reviewed_script(dep, write_config, signoff, tmp_path, capsys):
    cfg = write_config()
    plan_code = dep.main(["plan", "--config", str(cfg), "--out-dir", str(tmp_path / "r0")],
                         executor=lambda s: 1, env={})
    reviewed = capsys.readouterr().out
    code, ran, _ = live(dep, cfg, signoff(), tmp_path, capsys)
    assert plan_code == 0 and code == 0 and ran == [reviewed], "--live must run the dry-run text, unchanged"
    assert (tmp_path / "rendered" / "taskdef.json").is_file()


def test_without_live_flag_a_signed_off_run_is_still_dry(dep, write_config, signoff, tmp_path, capsys):
    ran = []
    code = dep.main(["plan", "--config", str(write_config()), "--signoff", str(signoff()),
                     "--out-dir", str(tmp_path / "r")], executor=lambda s: ran.append(s) or 0, env={})
    assert code == 0 and not ran


def test_signoff_status_counts_public_boxes_only_when_needed(dep, signoff):
    ok, missing = dep.signoff_status(signoff(), need_public=False)
    assert ok and missing == []
    ok, missing = dep.signoff_status(signoff(), need_public=True)
    assert not ok and len(missing) == 2


# ----------------------------------------------------------------------------------------- teardown
RESOURCE_PAIRS = [  # (created by, deleted by)
    ("aws budgets create-budget", "aws budgets delete-budget"),
    ("aws ecr create-repository", "aws ecr delete-repository"),
    ("aws logs create-log-group", "aws logs delete-log-group"),
    ("aws iam create-role", "aws iam delete-role"),
    ("aws iam attach-role-policy", "aws iam detach-role-policy"),
    ("aws ecs create-cluster", "aws ecs delete-cluster"),
    ("aws ecs register-task-definition", "aws ecs deregister-task-definition"),
    ("aws ec2 create-security-group", "aws ec2 delete-security-group"),
    ("aws ecs create-service", "aws ecs delete-service"),
]


def test_teardown_deletes_every_resource_type_created(dep, write_config, capsys, tmp_path):
    cfg = write_config()
    deploy = "\n".join(commands(plan(dep, cfg, capsys, tmp_path)[1]))
    assert dep.main(["teardown", "--config", str(cfg)], env={}) == 0
    teardown = commands(capsys.readouterr().out)
    joined = "\n".join(teardown)
    for create, delete in RESOURCE_PAIRS:
        if create in deploy:
            assert delete in joined, f"the deploy runs `{create}` but the teardown has no `{delete}`"
    assert "--force" in teardown[first_index(teardown, "aws ecr delete-repository")], \
        "a repository with images is only deleted with --force"


def test_teardown_order(dep, write_config, capsys):
    assert dep.main(["teardown", "--config", str(write_config())], env={}) == 0
    t = commands(capsys.readouterr().out)
    assert first_index(t, "aws ecs delete-service") < first_index(t, "aws ecs delete-cluster")
    assert first_index(t, "aws iam detach-role-policy") < first_index(t, "aws iam delete-role")
    assert first_index(t, "aws ecs delete-service") < first_index(t, "aws ec2 delete-security-group")


# ----------------------------------------------------------------------------------------- task definition
def test_task_definition_is_valid_fargate_with_health_check_and_logs(dep, write_config):
    cfg = dep.load_config(write_config(), env={})
    td = dep.render_task_definition(cfg)
    json.dumps(td)
    assert td["requiresCompatibilities"] == ["FARGATE"] and td["networkMode"] == "awsvpc"
    assert td["cpu"] == "256" and td["memory"] == "512"
    (c,) = td["containerDefinitions"]
    assert c["image"] == f"{REGISTRY}/flowguard:{RELEASE}"
    assert {"containerPort": 8000, "protocol": "tcp"} in c["portMappings"]
    hc = c.get("healthCheck")
    assert hc and hc["command"][0] in ("CMD", "CMD-SHELL"), "the container needs a healthCheck"
    assert "/readyz" in " ".join(hc["command"]), "the health check must probe readiness, /readyz"
    log = c.get("logConfiguration")
    assert log and log["logDriver"] == "awslogs", "logs must go to CloudWatch (awslogs driver)"
    for key in ("awslogs-group", "awslogs-region", "awslogs-stream-prefix"):
        assert log["options"].get(key), f"logConfiguration.options needs {key} (required on Fargate)"
    assert log["options"]["awslogs-region"] == "eu-central-1"
    env = {e["name"]: e["value"] for e in c["environment"]}
    assert env.get("FLOWGUARD_MODEL_DIR", "").startswith("/") and env.get("FLOWGUARD_RELEASE") == RELEASE
    assert not any(re.search(r"(?i)secret|password|token|access_key", n) for n in env), \
        "secrets never go into plain environment variables of a task definition"


# ----------------------------------------------------------------------------------------- hygiene
CREDENTIAL_PATTERNS = [
    (re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), "an AWS access key id"),
    (re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*\S{20,}"), "a secret access key"),
    (re.compile(r"(?<![\d.])\d{12}(?![\d.])"), "a 12-digit AWS account id"),
]


def test_no_credentials_or_account_ids_in_the_lab(target):
    hits = []
    for path in target.rglob("*"):
        if not path.is_file() or path.suffix in (".whl", ".pyc", ".npz") or "__pycache__" in path.parts:
            continue
        text = path.read_text(errors="ignore")
        for pattern, what in CREDENTIAL_PATTERNS:
            for m in pattern.finditer(text):
                hits.append(f"{path.relative_to(target)}: {what}: {m.group(0)[:8]}...")
    assert not hits, "credentials or account ids must never be committed:\n" + "\n".join(hits)


def test_local_config_and_rendered_files_are_git_ignored(target):
    ignore = (target / "deploy" / ".gitignore").read_text().split()
    assert "config.toml" in ignore and any(x.startswith("rendered") for x in ignore)
