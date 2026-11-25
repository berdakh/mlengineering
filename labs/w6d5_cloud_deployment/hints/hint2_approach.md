# w6d5 hint 2: the approach

**Task 3 (`load_config`).**
1. `release = str(cfg["app"].get("release", ""))`; reject `"latest"`; accept `RELEASE.match(...)` or
   `PLACEHOLDER.fullmatch(...)`; otherwise `raise ConfigError("app.release ...")`.
2. For a non-empty, non-placeholder `allowed_cidr`, parse with `ipaddress.ip_network(cidr, strict=True)`
   (catch `ValueError`); if `net.prefixlen < net.max_prefixlen` and not `allow_public`, raise.

**Task 4 (`deploy_script`).** Write the script as one module-level string template with `${NAME}`-style
placeholders (`string.Template`) and fill it with `_vars(cfg)` plus two extra values: the managed policy
ARN and an `INGRESS` line that is either the `authorize-security-group-ingress` command or a comment.
Bash's own `$` must be written `$$` inside a `string.Template`. For the security group, capture its id in
a shell variable: `SG_ID=$$(aws ec2 create-security-group ... --query GroupId --output text)`.

Task definition: add to the container definition

* `"healthCheck"`: `command` (`["CMD-SHELL", "<a command that fails unless /readyz answers 200>"]`),
  `interval`, `timeout`, `retries`, `startPeriod`;
* `"logConfiguration"`: `"logDriver": "awslogs"` and `options` with `awslogs-group` (`/ecs/${NAME}`),
  `awslogs-region` and `awslogs-stream-prefix` (required on Fargate).

The image has Python but not curl, so the health-check command uses `python -c "import urllib.request; ..."`.

**Task 5.** Same template approach. Delete: service (scale to 0, delete with `--force`, wait inactive),
cluster, task-definition revisions (loop over `list-task-definitions --family-prefix`), security group
(look its id up by name and VPC), log group, repository (`--force`), detach policy, delete role, budget.

**Task 6.** A box is a list item `- [ ]` or `- [x]`. Track whether you are under a heading containing
"public" while reading lines; skip those boxes unless `need_public`. Zero boxes found means incomplete.
