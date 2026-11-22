"""w6d1 challenge: three broken builds, fixed. Static checks of the fixed files + the diagnosis."""
from __future__ import annotations

import re

import pytest

import w6d1_dockerlint as dl

SHELLS = ("sh", "/bin/sh", "bash", "/bin/bash")


def _load(target, name):
    path = target / "fixed" / name / "Dockerfile"
    if not path.is_file():
        pytest.fail(f"missing {path.relative_to(target)}", pytrace=False)
    parsed = dl.load_dockerfile(path)
    if not parsed.stages:
        pytest.fail(f"{path.relative_to(target)} has no FROM", pytrace=False)
    return parsed.final


def _pip(stage):
    return [i for i in stage.instructions if i.name == "RUN" and re.search(r"\bpip3?\b[^&;|]*\binstall\b", i.args)]


def _starts_uvicorn_on_all_interfaces(stage):
    argv, used = dl.effective_command(stage)
    assert used, "no CMD"
    assert argv is not None, "the command is in shell form: /bin/sh becomes PID 1 and swallows SIGTERM"
    if argv[0] in SHELLS:
        script = " ".join(argv[1:])
        assert re.search(r"(^|[;&|]\s*|\s)exec\s+uvicorn\b", script), (
            "the exec form starts a shell, and the shell stays PID 1 unless the script ends with "
            "`exec uvicorn ...`")
        assert "0.0.0.0" in script
    else:
        assert any(w.endswith("uvicorn") for w in argv), f"{argv} does not start uvicorn"
        assert dl.option_value(argv, "--host") == "0.0.0.0"


def _non_root(stage):
    users = [i for i in stage.instructions if i.name == "USER"]
    assert users and users[-1].args.split(":")[0] not in ("root", "0"), "the server still runs as root"
    user = users[-1].args.split(":")[0].strip()
    if not user.isdigit():
        assert any(i.name == "RUN" and re.search(rf"(useradd|adduser)\b[^&;|]*\b{re.escape(user)}\b", i.args)
                   for i in stage.instructions), f"user {user} is never created"


# ------------------------------------------------------------------ A: cache order

def test_a_installs_dependencies_before_copying_code(target):
    stage = _load(target, "a_cache")
    pip = _pip(stage)
    assert pip, "no pip install"
    for ins in stage.instructions:
        if ins.name in ("COPY", "ADD") and "from" not in ins.flags and ins.lineno < pip[0].lineno:
            sources = dl._copy_sources_dest(ins)[0]
            assert all(re.search(r"(requirements[^/]*\.(txt|lock)|pyproject\.toml)$", s) for s in sources), (
                f"line {ins.lineno}: COPY {sources} before pip install: a code edit still re-runs the install")
    after = " ".join(" ".join(dl._copy_sources_dest(i)[0]) for i in stage.instructions
                     if i.name == "COPY" and i.lineno > pip[0].lineno)
    assert "src" in after and "models" in after, "src/ and models/ must still be copied (after the install)"


def test_a_keeps_what_was_already_right(target):
    stage = _load(target, "a_cache")
    _starts_uvicorn_on_all_interfaces(stage)
    _non_root(stage)


# ------------------------------------------------------------------ B: signals and root

def test_b_server_receives_sigterm(target):
    _starts_uvicorn_on_all_interfaces(_load(target, "b_signals"))


def test_b_runs_as_unprivileged_user(target):
    _non_root(_load(target, "b_signals"))


# ------------------------------------------------------------------ C: build context

def _context(target):
    listing = target / "broken" / "c_context" / "context_listing.tsv"
    rows = [(line.split("\t")[0], int(line.split("\t")[1])) for line in listing.read_text().splitlines() if line]
    ignore_file = target / "fixed" / "c_context" / ".dockerignore"
    if not ignore_file.is_file():
        pytest.fail("missing fixed/c_context/.dockerignore", pytrace=False)
    ignore = dl.DockerIgnore.from_file(ignore_file)
    return rows, ignore


def test_c_context_is_small(target):
    rows, ignore = _context(target)
    sent = sum(size for path, size in rows if not ignore.excluded(path))
    assert sent < 2_000_000, f"{sent / 1e6:.1f} MB would still be sent to the builder (the image needs < 1 MB)"


def test_c_image_still_gets_what_it_needs(target):
    rows, ignore = _context(target)
    needed = [p for p, _ in rows if p == "requirements.txt" or p.startswith("models/")
              or (p.startswith("src/") and p.endswith(".py"))]
    missing = [p for p in needed if ignore.excluded(p)]
    assert not missing, f"excluded but needed by the image: {missing[:5]}"


@pytest.mark.parametrize("pattern,why", [
    (r"(^|/)\.env$", "the .env with credentials"),
    (r"(^|/)__pycache__/", "bytecode caches (at any depth)"),
    (r"(^|/)\.ipynb_checkpoints/", "notebook checkpoints (at any depth)"),
    (r"(^|/)runs/", "run outputs, including the ones nested under experiments/"),
    (r"^\.git/", "version history"),
    (r"^\.venv/", "the local virtual environment"),
])
def test_c_excludes(target, pattern, why):
    rows, ignore = _context(target)
    leaked = [p for p, _ in rows if re.search(pattern, p) and not ignore.excluded(p)]
    assert not leaked, f"{why} would be sent: {leaked[:3]}"


# ------------------------------------------------------------------ diagnosis

@pytest.mark.parametrize("section,keyword", [("A", r"cache"), ("B", r"SIGTERM|PID ?1"), ("C", r"context")])
def test_diagnosis_section(target, section, keyword):
    path = target / "DIAGNOSIS.md"
    assert path.is_file(), "missing DIAGNOSIS.md"
    text = path.read_text()
    match = re.search(rf"^## {section}\b.*?$(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    assert match, f"no '## {section}' section"
    body = match.group(1)
    assert len(re.findall(r"\w+", body)) >= 40, f"section {section}: explain symptom, mechanism, fix, verification"
    assert re.search(keyword, body, flags=re.I), f"section {section} does not explain the mechanism ({keyword})"
