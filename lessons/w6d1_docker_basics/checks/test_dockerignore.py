"""The .dockerignore contract (w6d1): what must stay out of the build context, what must stay in."""
from __future__ import annotations

import pytest

import w6d1_dockerlint as dl

MUST_EXCLUDE = {
    ".git/objects/pack/pack-1.pack": "version history (often hundreds of MB)",
    ".venv/lib/python3.12/site-packages/numpy/__init__.py": "your local virtual environment",
    "data/raw/skab/valve1/0.csv": "raw data",
    "runs/20261122-1015/metrics.json": "run outputs",
    "src/flowguard/__pycache__/api.cpython-312.pyc": "bytecode caches at ANY depth",
    "scripts/__pycache__/build_bundle.cpython-312.pyc": "bytecode caches at ANY depth",
    ".env": "local secrets",
}
MUST_INCLUDE = [
    "requirements.txt",
    "src/flowguard/api.py",
    "src/flowguard/schemas.py",
    "src/flowguard/bundle.py",
    "src/flowguard/inference.py",
    "models/flowguard-z/1.0.0/model.json",
    "models/flowguard-z/1.0.0/checksums.json",
]


def test_dockerignore_exists(target):
    assert (target / ".dockerignore").is_file(), (
        "no .dockerignore: `docker build .` sends the whole directory (.venv, data, .git ...) to the builder")


@pytest.mark.parametrize("path", sorted(MUST_EXCLUDE))
def test_excluded(path, ignore):
    assert ignore.excluded(path), (
        f"{path} ({MUST_EXCLUDE[path]}) would be in the build context. Remember: .dockerignore patterns "
        "are anchored at the context root, unlike .gitignore; use **/ to match at any depth.")


@pytest.mark.parametrize("path", MUST_INCLUDE)
def test_needed_files_stay_in_the_context(path, ignore):
    assert not ignore.excluded(path), f"{path} is excluded, but the image needs it"


def test_every_copy_source_is_in_the_context(dockerfile, target, ignore):
    for ins in dockerfile.instructions:
        if ins.name not in ("COPY", "ADD") or "from" in ins.flags:
            continue
        parsed = dl._copy_sources_dest(ins)
        for src in (parsed[0] if parsed else []):
            rel = src.strip("/")
            if rel in ("", "."):
                continue
            assert (target / rel).exists(), f"line {ins.lineno}: COPY source {src!r} does not exist"
            assert not ignore.excluded(rel), f"line {ins.lineno}: COPY source {src!r} is excluded by .dockerignore"
