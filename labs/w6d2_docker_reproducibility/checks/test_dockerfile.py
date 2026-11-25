"""The w6d2 Dockerfile contract: digest-pinned base, builder + runtime stages, hash-checked install,
nothing for building in the runtime stage, provenance labels; plus the w6d1 runtime properties."""
from __future__ import annotations

import re

import pytest

import w6d2_dockerlint as dl

DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
TOOLCHAIN = re.compile(r"\b(build-essential|gcc|g\+\+|clang|make|cmake|python3-dev|libpython3[\w.]*-dev|"
                       r"gfortran|cargo|rustc)\b")


def _final(dockerfile):
    return dockerfile.final


def test_there_is_a_builder_stage_and_a_runtime_stage(dockerfile):
    assert len(dockerfile.stages) >= 2, (
        "one stage only: build tools, caches and intermediate files of the dependency install end up "
        "in the runtime image. Use a builder stage and a runtime stage.")
    final = _final(dockerfile)
    copies_from = [i.flags.get("from") for i in final.instructions if i.name == "COPY" and "from" in i.flags]
    earlier = {s.name for s in dockerfile.stages[:-1]} | {str(s.index) for s in dockerfile.stages[:-1]}
    assert any(str(f).lower() in earlier for f in copies_from), \
        "the runtime stage copies nothing from the builder stage (COPY --from=<builder> ...)"


def test_every_external_base_image_is_pinned_by_digest(dockerfile):
    names = set()
    for stage in dockerfile.stages:
        image = stage.image
        if image.lower() in names:              # FROM builder (a previous stage)
            continue
        assert DIGEST.search(image), (
            f"FROM {image!r}: a tag such as 3.12-slim is a pointer that moves when the image is rebuilt "
            "upstream. Pin the content: python:3.12-slim@sha256:<64 hex digits> "
            "(docker buildx imagetools inspect python:3.12-slim prints it).")
        if stage.name:
            names.add(stage.name)


def test_the_runtime_base_is_the_slim_python_image(dockerfile):
    image = _final(dockerfile).image
    assert re.match(r"(docker\.io/)?(library/)?python:3\.(1[1-9])[\w.-]*-slim", image), \
        f"the runtime stage starts from {image!r}; use python:3.1x-slim (glibc, small)"


def test_the_lockfile_is_installed_in_hash_checking_mode(dockerfile):
    installs = [(s, i) for s in dockerfile.stages for i in s.instructions
                if i.name == "RUN" and re.search(r"\bpip3?\b[^&;|]*\binstall\b", i.args)]
    assert installs, "no pip install anywhere"
    locked = [i for _, i in installs if re.search(r"(-r|--requirement)[\s=]*\S*requirements\.lock", i.args)]
    assert locked, "no stage installs requirements.lock (pip install -r requirements.lock)"
    copied = any(i.name == "COPY" and "requirements.lock" in i.args for s in dockerfile.stages for i in s.instructions)
    assert copied, "requirements.lock is never copied into a stage"
    assert not any(re.search(r"requirements\.(txt|in)\b", i.args) for _, i in installs), \
        "an install still reads requirements.txt/.in: ranges resolve differently on every build"


def test_the_runtime_stage_does_not_resolve_or_compile_anything(dockerfile):
    final = _final(dockerfile)
    for ins in final.instructions:
        if ins.name != "RUN":
            continue
        assert not TOOLCHAIN.search(ins.args), (
            f"line {ins.lineno}: build toolchain installed in the runtime stage; compile in the builder")
        if re.search(r"\bpip3?\b[^&;|]*\binstall\b", ins.args):
            assert "--no-index" in ins.args, (
                f"line {ins.lineno}: the runtime stage installs from the package index. Install in the "
                "builder and COPY --from the result (or install local wheels with --no-index).")


def test_provenance_labels_come_from_build_arguments(dockerfile):
    final = _final(dockerfile)
    labels = " ".join(i.args for i in final.instructions if i.name == "LABEL")
    for key in ("org.opencontainers.image.version", "org.opencontainers.image.revision"):
        assert key in labels, f"LABEL {key}=... is missing in the runtime stage"
    revision = re.search(r'org\.opencontainers\.image\.revision="?(\$\{?\w+\}?)', labels)
    assert revision, "the revision label should come from a build argument (e.g. --build-arg REVISION=$(git rev-parse HEAD))"
    arg = revision.group(1).strip("${}")
    assert any(i.name == "ARG" and i.args.split("=")[0].strip() == arg for i in final.instructions), \
        f"ARG {arg} is not declared in the runtime stage (ARGs do not cross FROM)"


def test_runtime_properties_from_w6d1_are_kept(dockerfile, target, ignore):
    final = _final(dockerfile)
    users = [i for i in final.instructions if i.name == "USER"]
    assert users and users[-1].args.split(":")[0].strip() not in ("root", "0"), "the runtime stage runs as root"
    argv, used = dl.effective_command(final)
    assert used and argv is not None, "CMD must be exec form"
    assert any(w.endswith("uvicorn") for w in argv) and dl.option_value(argv, "--host") == "0.0.0.0"
    assert any(i.name == "HEALTHCHECK" for i in final.instructions), "HEALTHCHECK is missing"
    env = dl.stage_env(final)
    model_dir = env.get("FLOWGUARD_MODEL_DIR")
    assert model_dir, "ENV FLOWGUARD_MODEL_DIR is missing in the runtime stage"
    mapped = dl.image_path_to_context(final, model_dir, target, ignore)
    assert mapped is not None and (mapped / "model.json").is_file(), \
        f"FLOWGUARD_MODEL_DIR={model_dir} does not contain the bundle in the runtime image"
