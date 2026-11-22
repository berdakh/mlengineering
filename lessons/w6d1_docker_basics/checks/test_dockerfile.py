"""The Dockerfile contract (w6d1). Each test states one property of a production-sane image."""
from __future__ import annotations

import importlib
import re
import shlex
import sys

import pytest

import w6d1_dockerlint as dl

SECRET_NAME = re.compile(r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|ACCESS_?KEY|PRIVATE_?KEY|CREDENTIAL)", re.I)
DEP_SPECS = re.compile(r"(^|/)(requirements[^/]*\.(txt|lock|in)|pyproject\.toml|setup\.cfg|.*\.lock)$")


def _pip_installs(stage):
    return [i for i in stage.instructions if i.name == "RUN" and re.search(r"\bpip3?\b[^&;|]*\binstall\b", i.args)]


def _copies(stage):
    return [i for i in stage.instructions if i.name in ("COPY", "ADD") and "from" not in i.flags]


def _sources(ins):
    parsed = dl._copy_sources_dest(ins)
    return parsed[0] if parsed else []


def test_base_image_has_an_explicit_python_tag(final):
    image = final.image
    name, _, tag = image.split("@")[0].partition(":")
    assert name.split("/")[-1] == "python", f"base image {image!r}: use the official python image"
    assert tag and tag != "latest", (
        f"base image {image!r} has no tag or uses 'latest': the image you get changes without "
        "any change to your Dockerfile. Name the Python version, e.g. python:3.12-slim")
    assert re.match(r"3\.(1[1-9]|[2-9]\d)", tag), f"tag {tag!r}: the service needs Python >= 3.11"


def test_dependencies_are_installed_before_the_code_is_copied(final):
    pip = _pip_installs(final)
    assert pip, "no RUN pip install in the final stage"
    first_pip = pip[0]
    before = [c for c in _copies(final) if c.lineno < first_pip.lineno]
    assert before, "nothing is copied before the first pip install; copy requirements.txt first"
    for copy in before:
        for src in _sources(copy):
            norm = src.rstrip("/")
            assert DEP_SPECS.search(norm), (
                f"line {copy.lineno}: COPY {src!r} comes BEFORE `pip install` (line {first_pip.lineno}). "
                "Any change to that path invalidates the cache of every later layer, so editing one "
                "line of code reinstalls all dependencies. Copy only the dependency file(s) first.")
    assert re.search(r"(-r|--requirement)\s*\S*requirements", first_pip.args) or "pyproject" in " ".join(
        s for c in before for s in _sources(c)), (
        "the first pip install should install the pinned serving dependencies (-r requirements.txt)")
    later = [c for c in _copies(final) if c.lineno > first_pip.lineno]
    copied_later = " ".join(s for c in later for s in _sources(c))
    assert "src" in copied_later or copied_later.strip() in (".", "./"), \
        "copy the code (src/) after the dependency install"


def test_pip_does_not_keep_its_download_cache(final):
    env = dl.stage_env(final)
    flag_env = env.get("PIP_NO_CACHE_DIR", "").lower() in ("1", "true", "yes", "on")
    for ins in _pip_installs(final):
        assert "--no-cache-dir" in ins.args or flag_env, (
            f"line {ins.lineno}: pip keeps its wheel cache (~same size as the packages) in the layer. "
            "Use --no-cache-dir or ENV PIP_NO_CACHE_DIR=1")


def test_the_container_runs_as_an_unprivileged_user(final):
    users = [i for i in final.instructions if i.name == "USER"]
    assert users, "no USER instruction: the server would run as root inside the container"
    user = users[-1].args.strip().split(":")[0]
    assert user not in ("root", "0", ""), f"the last USER is {user!r}"
    if not user.isdigit():
        created = any(i.name == "RUN" and re.search(rf"(useradd|adduser)\b[^&;|]*\b{re.escape(user)}\b", i.args)
                      for i in final.instructions if i.lineno < users[-1].lineno)
        assert created, f"USER {user} is never created (useradd/adduser) before it is used"


def test_the_command_is_exec_form_uvicorn_on_all_container_interfaces(final):
    argv, used = dl.effective_command(final)
    assert used, "no CMD or ENTRYPOINT"
    assert argv is not None, (
        f"line {used[-1].lineno}: shell form. The container's PID 1 becomes /bin/sh, which does not "
        "forward SIGTERM: `docker stop` waits 10 s and then kills the server (exit 137). Use the "
        'JSON exec form: CMD ["uvicorn", ...]')
    assert any(word.endswith("uvicorn") for word in argv), f"the command {argv} does not start uvicorn"
    if argv[0] in ("sh", "/bin/sh", "bash", "/bin/bash"):
        pytest.fail("the exec form starts a shell; start uvicorn directly", pytrace=False)
    host = dl.option_value(argv, "--host")
    assert host == "0.0.0.0", (
        f"uvicorn listens on {host or '127.0.0.1 (its default)'!r}. Inside a container, 127.0.0.1 is "
        "the container's own loopback: the published port would reach nothing. Use --host 0.0.0.0; "
        "which HOST interface is exposed is decided by `docker run -p`.")
    assert (dl.option_value(argv, "--port") or "8000") == "8000", "uvicorn must listen on port 8000"


def test_port_8000_is_exposed(final):
    exposed = " ".join(i.args for i in final.instructions if i.name == "EXPOSE").split()
    assert any(p.split("/")[0] == "8000" for p in exposed), "EXPOSE 8000 documents the service port"


def test_healthcheck_asks_the_service_with_a_tool_the_image_has(final):
    checks = [i for i in final.instructions if i.name == "HEALTHCHECK"]
    assert checks, "no HEALTHCHECK: Docker cannot tell a running-but-broken server from a healthy one"
    hc = checks[-1]
    assert not hc.args.strip().upper().startswith("NONE"), "HEALTHCHECK NONE disables the check"
    assert re.search(r"/(readyz|healthz)", hc.args), "the HEALTHCHECK should request /readyz (or /healthz)"
    for tool in ("curl", "wget"):
        if re.search(rf"\b{tool}\b", hc.args):
            installed = any(i.name == "RUN" and re.search(rf"(apt-get|apt|apk)\b[^&;]*install[^&;]*\b{tool}\b", i.args)
                            for i in final.instructions)
            assert installed, (f"the HEALTHCHECK uses {tool}, which python:*-slim does not contain, so the check "
                               "always fails and the container is reported unhealthy. Use python -c with urllib, "
                               f"or install {tool}.")


def test_no_secrets_and_no_remote_downloads_in_the_recipe(dockerfile):
    for ins in dockerfile.instructions:
        if ins.name == "ADD":
            assert not re.search(r"https?://", ins.args), f"line {ins.lineno}: ADD from a URL is not reproducible"
        if ins.name in ("ENV", "ARG"):
            pairs = dl.parse_env(ins) if ins.name == "ENV" else dict([ins.args.strip().partition("=")[::2]])
            for key, value in pairs.items():
                assert not (SECRET_NAME.search(key) and value), (
                    f"line {ins.lineno}: {key} has a value in the Dockerfile. Image metadata and layers are "
                    "readable by anyone who can pull the image; pass secrets at run time instead.")
        if ins.name in ("COPY", "ADD"):
            for src in _sources(ins):
                assert not re.search(r"(^|/)(\.env|.*\.pem|.*\.key|id_rsa|credentials)", src), \
                    f"line {ins.lineno}: COPY of {src!r} puts a secret into a layer"


def test_the_image_layout_finds_the_app_and_the_model(final, target, ignore):
    """Follow WORKDIR/COPY/ENV as Docker would and check what the server will find at run time."""
    env = dl.stage_env(final)
    argv, _ = dl.effective_command(final)
    app_ref = next((w for w in (argv or []) if ":" in w and not w.startswith("-")), None)
    assert app_ref, "the command does not name the app (module:attribute)"
    module, _, attr = app_ref.partition(":")

    code_dirs = []
    for entry in filter(None, env.get("PYTHONPATH", "").split(":")):
        mapped = dl.image_path_to_context(final, entry, target, ignore)
        if mapped is not None and mapped.is_dir():
            code_dirs.append(mapped)
    installs_project = any(re.search(r"install\b[^&;|]*\s(\.|/app)(\s|$)", i.args) for i in _pip_installs(final))
    if installs_project:
        code_dirs.append(target / "src")
    assert code_dirs, ("inside the image, the package is neither on PYTHONPATH (ENV PYTHONPATH=<where src "
                       "was copied>) nor installed with pip, so uvicorn fails with ModuleNotFoundError")
    module_file = module.replace(".", "/") + ".py"
    home = next((d for d in code_dirs if (d / module_file).is_file()), None)
    assert home is not None, f"{module_file} is not under any of {code_dirs} in the image"
    sys.path.insert(0, str(home))
    try:
        for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
            del sys.modules[name]
        mod = importlib.import_module(module)
        assert callable(getattr(mod, attr, None)), f"{app_ref}: {attr} is not defined in {module}"
        bundle_mod = importlib.import_module("flowguard.bundle")
    finally:
        sys.path.remove(str(home))

    model_dir = env.get("FLOWGUARD_MODEL_DIR")
    assert model_dir, "ENV FLOWGUARD_MODEL_DIR is not set: the app would start but never be ready (503)"
    mapped = dl.image_path_to_context(final, model_dir, target, ignore)
    assert mapped is not None and mapped.is_dir(), (
        f"FLOWGUARD_MODEL_DIR={model_dir} is not a directory that a COPY puts into the image")
    try:
        bundle_mod.load_bundle(mapped)
    except bundle_mod.BundleError as exc:
        pytest.fail(f"FLOWGUARD_MODEL_DIR={model_dir} maps to {mapped.relative_to(target)}, which is not a "
                    f"loadable bundle: {exc}", pytrace=False)


def test_build_does_not_bake_in_the_training_tools(final):
    words = " ".join(shlex.quote(w) for i in _pip_installs(final) for w in i.args.split())
    assert "requirements-dev" not in words and not re.search(r"\b(pytest|scipy|jupyter|matplotlib)\b", words), \
        "the serving image installs development or training tools; install requirements.txt only"
