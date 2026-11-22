"""requirements.lock (w6d2): every package the image installs, pinned exactly, with hashes."""
from __future__ import annotations

import re

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

# Packages the service imports at run time, directly or through its dependencies. If one of them is
# missing from the lock, an install from the lock either fails in hash-checking mode or (without hashes)
# silently pulls whatever version is newest on build day.
RUNTIME_CLOSURE = {"fastapi", "starlette", "pydantic", "pydantic-core", "uvicorn", "anyio", "h11", "click",
                   "numpy", "pandas", "python-dateutil", "tzdata", "typing-extensions", "annotated-types"}
NOT_FOR_SERVING = {"pytest", "scipy", "matplotlib", "jupyter", "jupyterlab", "ipython", "ruff", "httpx"}


def parse_lock(text: str) -> dict[str, dict]:
    """{name: {"spec": "==1.2.3", "hashes": [...], "line": "..."}} from a pip requirements file."""
    entries, current = {}, None
    logical = re.sub(r"\\\s*\n", " ", text)
    for raw in logical.splitlines():
        line = raw.split(" #", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            continue                                   # options such as --index-url
        hashes = re.findall(r"--hash=sha256:([0-9a-f]{64})", line)
        req_text = re.split(r"\s--", line, maxsplit=1)[0].strip()
        req = Requirement(req_text)
        name = canonicalize_name(req.name)
        entries[name] = {"spec": str(req.specifier), "hashes": hashes, "line": req_text}
        current = name
    return entries


@pytest.fixture(scope="module")
def lock(target):
    path = target / "requirements.lock"
    if not path.is_file():
        pytest.fail("no requirements.lock: compile it from requirements.in (lesson section 4.2)", pytrace=False)
    entries = parse_lock(path.read_text())
    if not entries:
        pytest.fail("requirements.lock contains no requirements", pytrace=False)
    return entries


def test_every_package_is_pinned_to_one_exact_version(lock):
    loose = {n: e["line"] for n, e in lock.items() if not re.fullmatch(r"==[^,*]+", e["spec"])}
    assert not loose, f"not pinned with == to one version: {loose}"


def test_every_package_has_a_sha256_hash(lock):
    missing = sorted(n for n, e in lock.items() if not e["hashes"])
    assert not missing, (
        f"no --hash=sha256:... for {missing}. Without hashes, '==1.2.3' trusts whatever file the index "
        "serves under that name today; with them pip refuses anything else (hash-checking mode).")


def test_the_lock_contains_the_full_runtime_closure(lock):
    missing = sorted(RUNTIME_CLOSURE - set(lock))
    assert not missing, (
        f"transitive dependencies missing from the lock: {missing}. Pinning only the top-level packages "
        "leaves their dependencies to be resolved on build day.")


def test_locked_versions_satisfy_requirements_in(lock, target):
    for line in (target / "requirements.in").read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        req = Requirement(line)
        name = canonicalize_name(req.name)
        assert name in lock, f"{req.name} from requirements.in is not in the lock"
        version = lock[name]["spec"].removeprefix("==")
        assert req.specifier.contains(version, prereleases=True), \
            f"{name}=={version} does not satisfy '{req}' in requirements.in: was the lock compiled from it?"


def test_development_tools_are_not_locked_for_serving(lock):
    found = sorted(NOT_FOR_SERVING & set(lock))
    assert not found, f"{found} are development or training tools; they do not belong in the serving lock"
