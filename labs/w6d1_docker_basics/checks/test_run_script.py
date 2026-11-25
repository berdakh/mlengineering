"""run_container.sh (w6d1): builds a tagged image and publishes the port on loopback only."""
from __future__ import annotations

import re
import shlex
import subprocess


def _commands(target):
    text = (target / "run_container.sh").read_text()
    joined = re.sub(r"\\\n", " ", text)
    lines = [ln.strip() for ln in joined.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    return [ln for ln in lines if ln.startswith("docker ")]


def test_script_exists_and_is_valid_bash(target):
    script = target / "run_container.sh"
    assert script.is_file(), "no run_container.sh"
    proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, f"bash -n: {proc.stderr}"


def test_script_builds_a_tagged_image(target):
    builds = [c for c in _commands(target) if c.startswith("docker build")]
    assert builds, "no `docker build` in run_container.sh"
    assert re.search(r"\s(-t|--tag)[\s=]", builds[0]), "tag the image (-t name:version) so `docker run` can name it"


def test_script_publishes_on_loopback_only(target):
    runs = [c for c in _commands(target) if c.startswith("docker run")]
    assert runs, "no `docker run` in run_container.sh"
    words = shlex.split(runs[0].replace('"', " ").replace("'", " "), posix=True)
    published = [words[i + 1] for i, w in enumerate(words[:-1]) if w in ("-p", "--publish")]
    published += [w.split("=", 1)[1] for w in words if w.startswith("--publish=")]
    assert published, "the container port is not published (-p): nothing outside the container can reach it"
    for spec in published:
        parts = spec.split(":")
        assert len(parts) == 3 and parts[0] == "127.0.0.1", (
            f"-p {spec}: without a host IP, Docker listens on ALL interfaces (0.0.0.0), reachable from your "
            "network, and Docker's own iptables rules bypass ufw. Use -p 127.0.0.1:<port>:8000")
        assert parts[2].split("/")[0] == "8000", f"-p {spec}: the container listens on 8000"
    assert "--rm" in words, "use --rm so stopped containers do not pile up"
    assert "--privileged" not in words and "--network=host" not in runs[0] and "host" != _network(words), \
        "the service needs neither --privileged nor host networking"


def _network(words):
    for i, w in enumerate(words[:-1]):
        if w in ("--network", "--net"):
            return words[i + 1]
    return None
