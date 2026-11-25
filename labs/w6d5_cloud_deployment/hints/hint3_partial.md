# w6d5 hint 3: partial implementation

`load_config` validation (complete):

```python
    release = str(cfg["app"].get("release", ""))
    if release == "latest" or not (RELEASE.match(release) or PLACEHOLDER.fullmatch(release)):
        raise ConfigError(f"app.release must be a git SHA (7-40 lowercase hex), not {release!r}")

    cidr = str(cfg["network"].get("allowed_cidr", "") or "")
    allow_public = bool(cfg["network"].get("allow_public", False))
    if cidr and not PLACEHOLDER.fullmatch(cidr):
        try:
            net = ipaddress.ip_network(cidr, strict=True)
        except ValueError as exc:
            raise ConfigError(f"network.allowed_cidr is not a valid CIDR: {cidr!r}") from exc
        if net.prefixlen < net.max_prefixlen and not allow_public:
            raise ConfigError(f"network.allowed_cidr {cidr} is public access: set network.allow_public")
```

The start and the end of the deploy template (fill in the middle, steps 2-7 of section 2.1). Write
each command on one line in your file: the checks look at whole lines.

```python
_DEPLOY = """\
#!/usr/bin/env bash
set -euo pipefail
export AWS_PROFILE=${PROFILE} AWS_REGION=${REGION}
aws sts get-caller-identity
aws budgets create-budget --account-id ${ACCOUNT_ID} --budget file://deploy/rendered/budget.json --notifications-with-subscribers file://deploy/rendered/budget-notifications.json
# ... repository, lifecycle, login, build, push, logs, role, cluster, task definition ...
SG_ID=$$(aws ec2 create-security-group --group-name ${SG} --description "${NAME} service" --vpc-id ${VPC_ID} --query GroupId --output text)
${INGRESS}
aws ecs create-service --cluster ${CLUSTER} --service-name ${SERVICE} --task-definition ${NAME} --desired-count 1 --launch-type FARGATE --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[$$SG_ID],assignPublicIp=ENABLED}"
aws ecs wait services-stable --cluster ${CLUSTER} --services ${SERVICE}
"""
```

`signoff_status` skeleton:

```python
_BOX = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+?)\s*$")

def signoff_status(path, need_public=False):
    path = Path(path)
    if not path.is_file():
        return False, [f"{path} does not exist"]
    unticked, in_public, seen = [], False, 0
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("#"):
            in_public = "public" in line.lower()
            continue
        ...   # match _BOX; skip public boxes unless need_public; count; collect unticked
    if seen == 0:
        return False, ["no check boxes found"]
    return not unticked, unticked
```
