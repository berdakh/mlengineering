"""Local delivery tooling for the w6d6 lab: a registry, two environments, promotion, seeded incidents.
GIVEN: you do not need to edit this file (but read `deploy` and `promote`; the lesson discusses them).

Everything runs on this machine with Docker. Every port is published on 127.0.0.1 only.

    python ops/fgops.py registry-up                 # a local OCI registry on 127.0.0.1:5005
    python ops/fgops.py build [--release SHA]       # build service/, tag with the git SHA, push
    python ops/fgops.py deploy staging <release|image@digest>
    python ops/fgops.py promote --from staging --to production
    python ops/fgops.py status                      # containers, readiness, /version per environment
    python ops/fgops.py history [ENV]               # the release history (ops/state/releases.json)
    python ops/fgops.py scenario 1|2|3              # seed an incident in production (see the lesson)
    python ops/fgops.py reset                       # restore env files and runtime settings
    python ops/fgops.py cleanup                     # remove every container and image this lab made

Run from the lab directory. Behind a TLS-intercepting proxy, put wheels in service/wheels/ and export
PIP_INSTALL_OPTS="--no-index --find-links=/srv/wheels" before `build` (the lesson explains why).

Design rules this tool follows (and the lesson asks you to defend):
* An image is built once, tagged with the git SHA, and pushed. Environments run it **by digest**
  (``image@sha256:...``), never by tag, so what was tested in staging is byte-for-byte what runs in
  production. Promotion copies a digest between environments; it never rebuilds.
* Configuration that differs between environments lives in ops/env/<env>.env and ops/env/runtime.json,
  not in the image.
* Every deployment appends to ops/state/releases.json: environment, release, digest, time, and whether
  the new container became ready ("good") or not ("failed").
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parents[1]
OPS = LAB / "ops"
STATE = OPS / "state"
HISTORY = STATE / "releases.json"
BUILDS = STATE / "builds.json"
REGISTRY = "127.0.0.1:5005"
IMAGE = f"{REGISTRY}/flowguard"
REGISTRY_CONTAINER = "fgops-registry"
ENVIRONMENTS = ("staging", "production")
DEFAULT_ENV = {
    env: (f"# Environment of the {env} container (docker run --env-file). FLOWGUARD_RELEASE is added by\n"
          "# `ops/fgops.py deploy` from the image being deployed, so it can never disagree with the image.\n"
          f"FLOWGUARD_ENV={env}\nFLOWGUARD_MODEL_DIR=/models/flowguard-z/1.0.0\nFLOWGUARD_LOG_LEVEL=INFO\n")
    for env in ENVIRONMENTS
}
DEFAULT_RUNTIME = {"staging": {"port": 8101, "memory": "256m", "cpus": "0.5"},
                   "production": {"port": 8102, "memory": "256m", "cpus": "0.5"}}


class OpsError(RuntimeError):
    pass


# --------------------------------------------------------------------------------------- helpers
def docker(*args: str, check: bool = True) -> str:
    proc = subprocess.run(["docker", *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise OpsError(f"docker {' '.join(args[:3])} ... failed: {proc.stderr.strip()[-400:]}")
    return proc.stdout.strip()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _load(path: Path, default):
    return json.loads(path.read_text()) if path.is_file() else default


def _save(path: Path, data) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    tmp.replace(path)


def load_history() -> list[dict]:
    return _load(HISTORY, {"entries": []})["entries"]


def save_history(entries: list[dict]) -> None:
    _save(HISTORY, {"entries": entries})


def runtime() -> dict:
    return json.loads((OPS / "env" / "runtime.json").read_text())


def container(env: str) -> str:
    return f"fgops-{env}"


def git_release() -> str:
    out = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, cwd=LAB)
    if out.returncode != 0:
        raise OpsError("not in a git repository; pass --release <hex sha>")
    return out.stdout.strip()


def resolve(ref: str) -> tuple[str, str]:
    """A release id or ``image@sha256:...`` -> (release, digest). Always returns a digest."""
    builds = _load(BUILDS, {})
    if "@sha256:" in ref:
        digest = ref.split("@", 1)[1]
        release = next((r for r, d in builds.items() if d == digest), "unknown")
        return release, digest
    if ref in builds:
        return ref, builds[ref]
    raise OpsError(f"unknown release {ref!r}; build it first (known: {sorted(builds)})")


def http_status(port: int, path: str) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=2) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
        return 0


# --------------------------------------------------------------------------------------- commands
def registry_up() -> None:
    running = docker("ps", "-q", "-f", f"name=^{REGISTRY_CONTAINER}$")
    if running:
        print(f"registry already running on {REGISTRY}")
        return
    docker("rm", "-f", REGISTRY_CONTAINER, check=False)
    docker("run", "-d", "--name", REGISTRY_CONTAINER, "-p", "127.0.0.1:5005:5000", "registry:3")
    print(f"registry running on {REGISTRY}")


def build(release: str | None = None, service_dir: Path | None = None, quiet: bool = False) -> tuple[str, str]:
    release = release or git_release()
    service_dir = service_dir or LAB / "service"
    tag = f"{IMAGE}:{release}"
    import os
    opts = os.environ.get("PIP_INSTALL_OPTS", "")
    docker("build", "-q", "--build-arg", f"PIP_INSTALL_OPTS={opts}", "-t", tag, str(service_dir))
    docker("push", tag)
    digests = json.loads(docker("image", "inspect", "-f", "{{json .RepoDigests}}", tag))
    digest = next(d.split("@", 1)[1] for d in digests if d.startswith(IMAGE + "@"))
    builds = _load(BUILDS, {})
    builds[release] = digest
    _save(BUILDS, builds)
    if not quiet:
        print(f"built and pushed {tag}\n  digest {digest}")
    return release, digest


def run_args(env: str, release: str, digest: str) -> list[str]:
    """The exact `docker run` arguments for an environment (also used by ops/rollback.py)."""
    rt = runtime()[env]
    return ["run", "-d", "--name", container(env),
            "--env-file", str(OPS / "env" / f"{env}.env"), "-e", f"FLOWGUARD_RELEASE={release}",
            "-p", f"127.0.0.1:{rt['port']}:8000", "--memory", rt["memory"], "--memory-swap", rt["memory"],
            "--cpus", str(rt["cpus"]), "--health-interval", "3s", "--health-start-period", "5s",
            f"{IMAGE}@{digest}"]


def deploy(env: str, ref: str, wait: float = 40.0, note: str = "", quiet: bool = False) -> dict:
    """Replace the environment's container with image@digest; record whether it became ready."""
    if env not in ENVIRONMENTS:
        raise OpsError(f"unknown environment {env!r}")
    release, digest = resolve(ref)
    docker("rm", "-f", container(env), check=False)
    docker(*run_args(env, release, digest))
    port, status, deadline = runtime()[env]["port"], "failed", time.time() + wait
    while time.time() < deadline:
        state = docker("inspect", "-f", "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
                       container(env), check=False)
        if state.startswith("exited"):
            break
        if state.endswith("healthy") and not state.endswith("unhealthy") and http_status(port, "/readyz") == 200:
            status = "good"
            break
        time.sleep(0.5)
    entry = {"env": env, "release": release, "image": IMAGE, "digest": digest, "deployed_at": _now(),
             "status": status, "note": note}
    entries = load_history()
    entries.append(entry)
    save_history(entries)
    if not quiet:
        print(f"{env}: {IMAGE}@{digest[:19]}... release {release} -> {status}")
    return entry


def current(env: str) -> dict | None:
    entries = [e for e in load_history() if e["env"] == env]
    return max(entries, key=lambda e: e["deployed_at"]) if entries else None


def promote(src: str, dst: str) -> dict:
    cur = current(src)
    if cur is None or cur["status"] != "good":
        raise OpsError(f"{src} has no good deployment to promote (current: {cur})")
    return deploy(dst, f"{cur['image']}@{cur['digest']}", note=f"promoted from {src}")


def status() -> None:
    for env in ENVIRONMENTS:
        port = runtime()[env]["port"]
        state = docker("inspect", "-f", "{{.State.Status}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}} "
                       "health={{if .State.Health}}{{.State.Health.Status}}{{end}}", container(env), check=False)
        version = ""
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/version", timeout=2) as r:
                version = r.read().decode()
        except Exception:  # noqa: BLE001
            version = "-"
        print(f"{env:<11} {state or 'no container'} readyz={http_status(port, '/readyz')} version={version}")


def history(env: str | None) -> None:
    for e in load_history():
        if env is None or e["env"] == env:
            print(f"{e['deployed_at']}  {e['env']:<11} {e['release']:<14} {e['digest'][:19]}...  "
                  f"{e['status']:<11} {e.get('note', '')}")


# --------------------------------------------------------------------------------------- incidents
def _set_env_var(env: str, key: str, value: str) -> None:
    path = OPS / "env" / f"{env}.env"
    lines = [ln for ln in path.read_text().splitlines() if not ln.startswith(f"{key}=")]
    path.write_text("\n".join(lines + [f"{key}={value}"]) + "\n")


def scenario(n: int) -> None:
    """Seed incident ``n`` in production. Deliberately terse: diagnosing it is the exercise."""
    cur = current("production")
    if cur is None:
        raise OpsError("deploy something to production first (lesson, task 2)")
    if n == 1:
        _set_env_var("production", "FLOWGUARD_MODEL_DIR", "/models/flowguard-z/1.0.1")
        deploy("production", f"{cur['image']}@{cur['digest']}", wait=15, note="config change", quiet=True)
    elif n == 2:
        with tempfile.TemporaryDirectory() as tmp:
            svc = Path(tmp) / "service"
            shutil.copytree(LAB / "service", svc, ignore=shutil.ignore_patterns("__pycache__"))
            model = svc / "models" / "flowguard-z" / "1.0.0" / "model.json"
            model.write_text(model.read_text().replace('"threshold": 7.244130714098134',
                                                       '"threshold": 6.5'))
            release = hashlib.sha1(model.read_bytes()).hexdigest()[:12]
            build(release, svc, quiet=True)
        deploy("staging", release, wait=15, note="threshold hotfix", quiet=True)
        deploy("production", release, wait=15, note="threshold hotfix (urgent, promoted by hand)", quiet=True)
    elif n == 3:
        rt = runtime()
        rt["production"]["memory"] = "64m"
        (OPS / "env" / "runtime.json").write_text(json.dumps(rt, indent=2) + "\n")
        deploy("production", f"{cur['image']}@{cur['digest']}", wait=25, note="right-size memory", quiet=True)
    else:
        raise OpsError("scenarios are 1, 2 and 3")
    print(f"Scenario {n} started. Production is unhappy. Diagnose it from the evidence "
          f"(status, history, docker logs, docker inspect) and write it up in DEBUG_LOG.md.")


def reset() -> None:
    for env, text in DEFAULT_ENV.items():
        (OPS / "env" / f"{env}.env").write_text(text)
    (OPS / "env" / "runtime.json").write_text(
        '{\n  "staging":    {"port": 8101, "memory": "256m", "cpus": "0.5"},\n'
        '  "production": {"port": 8102, "memory": "256m", "cpus": "0.5"}\n}\n')
    print("env files and runtime.json restored (containers and history unchanged)")


def cleanup() -> None:
    for env in ENVIRONMENTS:
        docker("rm", "-f", container(env), check=False)
    docker("rm", "-f", REGISTRY_CONTAINER, check=False)
    tags = docker("images", "--format", "{{.Repository}}:{{.Tag}}", IMAGE, check=False).split()
    for tag in tags:
        docker("rmi", "-f", tag, check=False)
    print(f"removed containers fgops-*, the registry, and {len(tags)} image tag(s); ops/state/ kept")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("registry-up")
    b = sub.add_parser("build")
    b.add_argument("--release")
    d = sub.add_parser("deploy")
    d.add_argument("env", choices=ENVIRONMENTS)
    d.add_argument("ref")
    d.add_argument("--note", default="")
    p = sub.add_parser("promote")
    p.add_argument("--from", dest="src", default="staging")
    p.add_argument("--to", dest="dst", default="production")
    sub.add_parser("status")
    h = sub.add_parser("history")
    h.add_argument("env", nargs="?")
    s = sub.add_parser("scenario")
    s.add_argument("n", type=int)
    sub.add_parser("reset")
    sub.add_parser("cleanup")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "registry-up":
            registry_up()
        elif args.cmd == "build":
            build(args.release)
        elif args.cmd == "deploy":
            deploy(args.env, args.ref, note=args.note)
        elif args.cmd == "promote":
            promote(args.src, args.dst)
        elif args.cmd == "status":
            status()
        elif args.cmd == "history":
            history(args.env)
        elif args.cmd == "scenario":
            scenario(args.n)
        elif args.cmd == "reset":
            reset()
        elif args.cmd == "cleanup":
            cleanup()
    except OpsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
